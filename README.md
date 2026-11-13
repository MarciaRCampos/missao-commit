# Missão Commit: Git e GitHub do zero

Curso-jogo de Git e GitHub da **Kora EduTech**, em 6 capítulos, com a história da Rita (analista sênior) ensinando o Téo (estagiário) na Kora Labs, uma startup de Brasília.

## Como abrir

Abra o arquivo `index.html` no navegador. Não precisa instalar nada.

## O que tem no jogo

- **Prova rápida** no início de cada capítulo: quem acerta tudo pode pular o capítulo.
- **Correção imediata**, sempre com a explicação do porquê.
- **Simulador de Git** dentro do jogo: `init`, `add`, `commit`, `log`, `diff`, `restore`, `branch`, `merge`, `remote`, `push`, `pull`.
- **Capítulo de portfólio**: o aluno escolhe 1, 2 ou 3 projetos e faz um de cada vez, terminando com repositório, README e push para o GitHub.
- **Entrevista final** com três respostas possíveis e feedback.
- **Certificado** em quatro níveis (Básico, Intermediário, Avançado e Portfólio completo), com imagem 1080 × 1350, PDF, código de verificação e botão para adicionar ao LinkedIn.
- **Narração em áudio** (pasta `audio/`), com a voz do navegador como alternativa quando o arquivo não existe.
- Tesouros escondidos, música, modo escuro e suporte a teclado (Esc volta).

## Progresso

O progresso fica salvo no navegador, na chave `mg_missao_commit_v1`.

## Para o site

- O jogo envia a pontuação de cada capítulo à página que o hospeda, por `postMessage`, no formato `{jogo, capitulo, estrelas}`.
- O endereço da página de verificação do certificado pode ser definido em `window.__KORA_VERIFICA__`; sem isso, o jogo usa `<origem>/verificar`.

O método segue o Círculo Dourado (por quê, como, o quê), sem citar o nome da técnica ao aluno.
