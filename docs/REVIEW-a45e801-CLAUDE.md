# Parecer do Claude sobre a45e8014 (26/10 ~23h30 PY)

Base: clone público de github.com/rafaorlando3/proof-before-pay em a45e801, diff contra minha árvore v2.2, leitura de
python/pbp_guard/decision.py, cls/pbp/{API,Review,Agent,Operation/Agent,Operation/Replay,Process/Decide,UI}.cls e
docs/validation/*. Sem IRIS aqui: parecer de código, não de execução.

## Concordo (sem ressalva)
1. Guard de contexto (decision.py + Replay.ValidateContext): referências citadas têm de existir na saída real das
   ferramentas; flags coerentes com o contrato v1; "missing" só com null; 5 ferramentas obrigatórias; falha vira
   escalada selada com o "missing" declarado preservado (Decide.OnAgent). É a resposta certa aos 3 encerramentos
   incorretos reproduzidos. Não interpreta instruções dentro dos dados: correto.
2. API: CORS=0, header X-PBP-Request, Content-Type JSON obrigatório, corpo limitado e guardado antes de qualquer
   mutação, rs.%Get em todas as leituras, Cache-Control no-store, verificação do recibo contra Ledger.Audit.
3. Review.Act com expectedCommitment obrigatório e reviewed_version_changed; nota via %FormValues.SetAt/GetAt
   ("pbp_note"); AssignTask + %Save antes de CompleteTask; recusas com motivo.
4. Agent.cls: modelo explícito obrigatório; provedor restrito a gemini|openai|anthropic; override de base_url com
   "gemini" rejeitado (o transporte real do teste foi provider=openai no endpoint compatível do Google; o README e o
   artigo devem dizer isso com essas palavras). Custo -1 quando desconhecido; ^pbp.live com último sucesso real.
5. pbp.UI servindo o console com UTF-8/no-store (ServeFiles respondia ISO-8859).

## Ressalvas e propostas (nenhuma bloqueia)
A. decision.py, check_context: `if (missing or observed_missing(tools)) and not human: return 'missing_evidence_requires_human'`
   faz QUALQUER ausência (por exemplo evidence.delivery_proof nulo num accept_order sem dinheiro) exigir revisor.
   É fail-closed e aceitável na v1, mas na prática zera a autonomia do agente em ações sem dinheiro, e o jurado vai ver
   "requires human" em quase tudo que passou pelo modelo. Proposta: exigir humano só quando a ausência é crítica
   (order_lookup, payment_status, policy_lookup, refund_target) OU a ação move dinheiro; ausências de evidência
   complementar em ação sem dinheiro ficam seladas como ignorância, sem revisor. Se preferir manter, escrever a regra
   no README como decisão explícita de v1.
B. Proposta recusada: hoje a proposta original do modelo só sobrevive no trace de mensagens (DecisionResponse).
   Para o revisor e para o artigo, proponho 1 propriedade nova em pbp.Data.Decision (ProposalJSON, MAXLEN "") gravada
   no caminho de falha de Decide.OnAgent (action, flags, amount, refs, missing e reason do guard), e o pbp.API
   expondo `decision.proposal` quando existir. O console v2.3 já renderiza `dec.proposal` se vier.
C. pbp.API.SealObj: expor `ledger_state` (seal.LedgerState) e `source` (seal.Source). O console v2.3 já lê
   `s.ledger_state` para mostrar "ledger refused: <motivo>" e mudar o texto do botão (Acknowledge x Approve refund).
D. Haiku escreveu "18990 BRL" na justificativa (minor units): no prompt do agente, acrescentar uma linha "amounts in
   the tools are minor units (cents); write them as such or convert explicitly (18990 minor = 189.90 BRL)". Fica no
   pbp.Agent (INSTRUCTIONS), que é meu; incluo no próximo delta se você concordar.
E. GPT sem temperature sob require_parameters: registrar no artigo como achado do EAP (temperatura efetiva
   desconhecida) e, no app, gravar em pbp.Data.Decision o que o gateway realmente enviou (temperature efetiva ou
   "omitted"), para não selar temperature 0 quando não foi enviada. Hoje o registro sela model.temperature=0 sempre.
   Proposta: pbp.Msg.DecisionResponse.Temperature recebe "" quando omitida e o registro sela "temperature": null?
   O validador S0 exige número em model.temperature; alternativa: selar -1 com nota no README. Decida você; eu ajusto
   o validador só se for necessário (mudança de schema é cara: evitar).
F. docs/validation/live-provider-smoke.json e gemini-direct-smoke.json: ótimos para o artigo "models and costs". Falta
   um campo "billing_verified": false explícito nos dois (hoje está em prosa no canal).

## Matriz oculta (entregue junto)
hidden/: 40 casos + gabarito + score.py + EXPORT.sql + README. Fora do repositório público. Ver C-.
