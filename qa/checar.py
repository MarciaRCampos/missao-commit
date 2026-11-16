#!/usr/bin/env python3
"""Verificador de curso-jogo Kora EduTech.

Roda o HTML num navegador, lê a estrutura do curso e procura os erros que
escapam numa leitura humana. Uso:

    python3 checar.py /caminho/do/jogo.html

Sai com código 1 se achar ERRO; AVISOs não derrubam a execução.
"""
import asyncio, json, re, sys, unicodedata
from difflib import SequenceMatcher
from playwright.async_api import async_playwright

ERROS, AVISOS = [], []
def erro(c, m): ERROS.append(f"[{c}] {m}")
def aviso(c, m): AVISOS.append(f"[{c}] {m}")

def norm(t):
    t = unicodedata.normalize('NFKD', (t or '').lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9 ]', ' ', re.sub(r'\s+', ' ', t)).strip()

LER = """() => {
  const F = s => ({t:s.t, k:s.k, id:s.id, w:s.w, s:s.s, q:s.q, opts:s.opts, a:s.a,
                   ok:s.ok, no:s.no, goal:s.goal, cmd:s.cmd, why:s.why, res:s.res,
                   prova: s.t==='p' ? (typeof PROVA!=='undefined' ? PROVA[s.ch] : null) : null});
  return {
    caps: CH.map((c,i) => ({i, titulo:c.titulo, rid:c.rid, kbase:c.kbase, koff:c.koff,
                            steps:c.steps.map(F)})),
    audio: typeof AUDIO_KEYS !== 'undefined' ? AUDIO_KEYS : [],
    chavesSoltas: (() => { const t = document.documentElement.outerHTML; const r = new Set();
      for (const m of t.matchAll(/'(cap[0-9]+_k_[a-z]+)'/g)) r.add(m[1]);
      for (const m of t.matchAll(/say\\([^;]*?'([a-z0-9_]+)'\\s*\\)/g)) r.add(m[1]);
      for (const m of t.matchAll(/'(anel_[a-z]+)'/g)) r.add(m[1]);
      for (const m of t.matchAll(/stepKey\\(si\\)\\s*\\+\\s*'(_[a-z]+)'/g)) r.add(m[1]);
      return [...r]; })(),
    textoTela: document.body.innerText
  };
}"""

def checar(d):
    caps, audio = d['caps'], set(d['audio'])
    ncaps = len(caps) - 1

    # ---------- 1. pergunta repetida dentro do capítulo e no curso inteiro ----------
    todas = []   # (cap, origem, pergunta, resposta_certa)
    for c in caps:
        for s in c['steps']:
            if s['t'] == 'p' and s.get('prova'):
                for q in s['prova']:
                    certas = [o['t'] for o in q['opts'] if o.get('b')]
                    todas.append((c, 'prova', q['q'], certas[0] if certas else None))
                    if len(certas) != 1:
                        erro('resposta', f"cap {c['i']} ({c['rid']}): prova com {len(certas)} respostas certas — {q['q'][:60]}")
            if s['t'] == 'q':
                opts = s.get('opts') or []
                a = s.get('a')
                todas.append((c, 'quiz', s.get('q'), opts[a] if isinstance(a, int) and a < len(opts) else None))
                if not isinstance(a, int) or a >= len(opts):
                    erro('resposta', f"cap {c['i']} ({c['rid']}): quiz sem resposta certa válida — {str(s.get('q'))[:60]}")
                if len(opts) < 2:
                    erro('resposta', f"cap {c['i']} ({c['rid']}): quiz com menos de 2 opções")

    for i in range(len(todas)):
        for j in range(i + 1, len(todas)):
            ci, oi, qi, ai = todas[i]
            cj, oj, qj, aj = todas[j]
            mesmoCap = ci['i'] == cj['i']
            sim = SequenceMatcher(None, norm(qi), norm(qj)).ratio()
            igualResp = ai and aj and norm(ai) == norm(aj)
            if mesmoCap and (sim > 0.7 or igualResp):
                erro('repetida', f"cap {ci['i']} ({ci['rid']}): {oi} e {oj} fazem a mesma pergunta "
                                 f"(semelhança {sim:.2f}, resposta igual: {bool(igualResp)}) — {str(qi)[:60]}")
            elif not mesmoCap and sim > 0.85:
                aviso('repetida', f"caps {ci['i']} e {cj['i']}: pergunta quase igual — {str(qi)[:60]}")

    # ---------- 2. estrutura de cada capítulo ----------
    for c in caps:
        if c['i'] == 0: continue
        tipos = [s['t'] for s in c['steps']]
        if tipos.count('p') != 1:
            erro('estrutura', f"cap {c['i']} ({c['rid']}): {tipos.count('p')} provas rápidas (esperado 1)")
        provas = [s for s in c['steps'] if s['t'] == 'p']
        if provas and not provas[0].get('prova'):
            erro('estrutura', f"cap {c['i']} ({c['rid']}): prova rápida sem perguntas — PROVA['{c['rid']}'] não existe")
        if not any(s.get('id') == 'resumo' for s in c['steps']):
            erro('estrutura', f"cap {c['i']} ({c['rid']}): sem cartão de resumo no fim")
        elif c['steps'][-1].get('id') != 'resumo' and c['steps'][-1]['t'] != 'e':
            aviso('estrutura', f"cap {c['i']} ({c['rid']}): o resumo não é o último passo")
        if not c.get('rid'):
            erro('estrutura', f"cap {c['i']}: sem rid (prova e resumo dependem dele)")

    rids = [c.get('rid') for c in caps if c.get('rid')]
    for r in set(rids):
        if rids.count(r) > 1 and r is not None:
            dono = [c['i'] for c in caps if c.get('rid') == r]
            erro('estrutura', f"rid '{r}' repetido nos capítulos {dono} — prova e resumo vão colidir")

    # ---------- 3. chaves de áudio ----------
    ks = [s['k'] for c in caps for s in c['steps'] if s.get('k')]
    ks += d.get('chavesSoltas', [])   # chaves usadas direto no código, fora dos passos
    for k in set(ks):
        if ks.count(k) > 1:
            erro('audio', f"chave de áudio duplicada: {k}")
    if audio:
        # chaves fixas (anéis, feedback de quiz, abertura da prova) não pertencem a um passo
        fixas = lambda k: k.startswith('anel_') or k.endswith('_certo') or k.endswith('_errado') or k in ('pergunta',)
        base = {k.rsplit('_certo',1)[0].rsplit('_errado',1)[0] for k in audio if fixas(k)}
        perdidas = sorted(k for k in audio - set(ks)
                          if not (fixas(k) and (k in ('pergunta',) or k.startswith('anel_') or
                                                any(b in ks for b in [k.rsplit('_certo',1)[0], k.rsplit('_errado',1)[0]]))))
        if perdidas:
            erro('audio', f"{len(perdidas)} gravações ficaram órfãs (a fala sumiu ou mudou de chave): {perdidas[:8]}")

    # ---------- 4. comando usado antes de ensinado ----------
    vistos, ordem = set(), []
    for c in caps:
        for s in c['steps']:
            texto = ' '.join(str(s.get(x) or '') for x in ('s', 'q', 'goal', 'why', 'ok', 'no'))
            if s.get('res'): texto += ' ' + ' '.join(s['res'].get('itens', [])) + ' ' + str(s['res'].get('onde', ''))
            if s.get('opts'): texto += ' ' + ' '.join(str(o.get('t', o) if isinstance(o, dict) else o) for o in s['opts'])
            if s.get('prova'):
                for q in s['prova']:
                    texto += ' ' + q['q'] + ' ' + ' '.join(o['t'] + ' ' + o['f'] for o in q['opts'])
            for m in re.findall(r'git [a-z\-]+', texto):
                vistos.add(m)
            if s['t'] == 'x' and s.get('cmd'):
                cmd = ' '.join(s['cmd'].split()[:2])
                # o texto da própria missão também ensina
                proprio = cmd in texto or cmd in str(s.get('goal') or '')
                ordem.append((c, cmd, cmd in vistos or proprio))
    for c, cmd, ensinado in ordem:
        if not ensinado:
            erro('nao-ensinado', f"cap {c['i']} ({c['rid']}): missão usa '{cmd}' sem ter sido citado antes")

    # ---------- 5. cronologia da história ----------
    DIAS = ['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo']
    seq = []
    for c in caps:
        for s in c['steps']:
            if s.get('w') == 'N' and s.get('s'):
                for n, dia in enumerate(DIAS):
                    if re.search(r'\b' + dia + r'(-feira)?\b', s['s'].lower()):
                        seq.append((c['i'], n, dia, s['s'][:40])); break
    semanas = 0
    for a, b in zip(seq, seq[1:]):
        if b[1] < a[1]: semanas += 1
        if b[1] < a[1] and 'seguinte' not in b[3].lower() and 'semana' not in b[3].lower():
            aviso('cronologia', f"cap {b[0]}: '{b[2]}' vem depois de '{a[2]}' (cap {a[0]}) sem marcar semana nova — {b[3]}")

    # ---------- 6. números defasados no texto ----------
    tela = d['textoTela']
    for m in re.findall(r'(?:história em|em)\s+(\d+)\s+cap[íi]tulos', tela):
        if int(m) != ncaps:
            erro('numero', f"a tela diz '{m} capítulos' e o curso tem {ncaps}")
    for c in caps:
        for s in c['steps']:
            for campo in ('s', 'why', 'ok', 'no'):
                t = str(s.get(campo) or '')
                if re.search(r'[úu]ltimo cap[íi]tulo|pr[óo]ximo cap[íi]tulo', t, re.I):
                    aviso('numero', f"cap {c['i']} ({c['rid']}): texto cita 'último/próximo capítulo' — conferir se ainda vale: {t[:70]}")
                m = re.search(r'cap[íi]tulo (\d+)', t, re.I)
                if m and int(m.group(1)) > ncaps:
                    erro('numero', f"cap {c['i']}: texto cita capítulo {m.group(1)}, que não existe")

async def main():
    url = 'file://' + (sys.argv[1] if len(sys.argv) > 1 else '/home/claude/missao-commit/index.html')
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
        pg = await (await b.new_context()).new_page()
        console = []
        pg.on('console', lambda m: console.append(m.text) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: console.append('pageerror: ' + str(e)))
        await pg.goto(url); await pg.wait_for_timeout(900)
        d = await pg.evaluate(LER)
        await b.close()
    for c in console: erro('console', c[:120])
    checar(d)
    print(f"{len(d['caps'])-1} capítulos · {sum(len(c['steps']) for c in d['caps'])} passos")
    for e in ERROS: print('❌', e)
    for a in AVISOS: print('⚠️ ', a)
    print(f"\n{len(ERROS)} erro(s), {len(AVISOS)} aviso(s)")
    sys.exit(1 if ERROS else 0)

asyncio.run(main())
