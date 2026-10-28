# Proof Before Pay: video production script v4.2.1

Base: Native runtime346ae94/backend6d03432; current revision ui/index.html fixes pending replay invalidation by same-signature polling. No model/core/Ledger change.. Target length 168 s. Master en, alternates pt-BR, es, zh-CN.

## Rules

- Every scene that shows the console carries a mode caption: RECORDED (rules + replayed agent decision) or LIVE (Gemini 3.8 Flash, past evidence only).
- Every scene where money appears carries the word sandbox or test ledger on screen.
- Case 56352df3 / receipt 340 is read-only history: show its sealed decision, approval and receipt; never approve it again.
- If an approval click is filmed, it is on a NEW synthetic case prepared before recording, with its real new case id and receipt id visible; one authenticated review, never a reset.
- Do not narrate or show the refund_destination tool field on the historical case 340 (its seal predates that field).
- Never present a rules (R1) refund as an agent decision; never label v4 as held-out; no percentages, no prize, no 'first', no article link until one exists.
- The approver shown is the authenticated synthetic reviewer login; Rafael is not named as approver.
- Narration is a synthetic voice generated from this script and is identified as such in the description and in the end card; it is not presented as Rafael's voice.
- On-screen text and CC must not contain the em dash character.
- Real continuous browser capture is trimmed for pace and preserves native screen size and capture time, without decorative camera movement. The separately compiled historical evidence report is explicitly labelled as a review document. No fabricated UI, terminal runs, approvals, or live inference.
- S03 uses the recorded synthetic case and recorded missing-recipient regression, not an unfilmed LIVE v4 scene. S06 uses actual tool output and an architecture overview; no Portal trace is implied.
- The new recorded case is video-demo:d83544a2, receipt test-refund:456, one authenticated synthetic reviewer approval; its recording does not enlarge the live-model benchmark.
- Rafael approved the four narration performances and languages on2026-10-28. Version4.2 copies the approved4.1.1 AAC/CC packets unchanged; visual approval is separate. No Codex pointer injection, decorative pan/zoom, artificial jitter or speed change.

## Scenes

### S01  00:00 to 00:18

Visual: Real continuous capture of video-flow:5751dd54 awaiting review, full native1920x1080 frame; no decorative pan/zoom.

Mode caption (EN): RECORDED proposal. Native IRIS workflow. Synthetic effects.

On screen (EN): A decision is not a payment.

Narration en: A customer pays twice. An AI proposes a refund. Before anything moves, can you prove what it saw, what was missing, and exactly what a person approved? This is Proof Before Pay.

Narration pt-BR: Um cliente paga duas vezes. Uma IA propõe o reembolso. Antes de qualquer movimento, você consegue provar o que ela viu, o que faltava e exatamente o que uma pessoa aprovou? Este é o Proof Before Pay.

Narration es: Un cliente paga dos veces. Una IA propone un reembolso. Antes de mover nada, ¿puedes demostrar qué vio, qué información faltaba y qué aprobó exactamente una persona? Esto es Proof Before Pay.

Narration zh-CN: 客户重复付款，人工智能建议退款。执行之前，能否证明它看到了什么、缺少哪些证据，以及审核人究竟批准了什么？这就是付款前留证，Proof Before Pay。


### S02  00:18 to 00:40

Visual: Real interactions with five actual native tool panels, full frame at original capture timing.

Mode caption (EN): RECORDED proposal. Native IRIS workflow. Synthetic effects.

On screen (EN): Five tools. Actual evidence.

Narration en: The application runs inside InterSystems IRIS. Five scoped tools read the order, payment events, payer history, evidence, and policy. This demonstration uses a recorded agent proposal on the native workflow. No live model call is hidden behind these scenes.

Narration pt-BR: A aplicação roda no InterSystems IRIS. Cinco ferramentas com escopo definido consultam o pedido, os pagamentos, o histórico, as evidências e a política. Esta demonstração usa uma proposta gravada no fluxo nativo. Nenhuma chamada ao modelo ao vivo é simulada nestas cenas.

Narration es: La aplicación se ejecuta en InterSystems IRIS. Cinco herramientas de alcance limitado consultan el pedido, los pagos, el historial, las pruebas y la política. Esta demostración usa una propuesta grabada en el flujo nativo. Estas escenas no simulan inferencia en vivo.

Narration zh-CN: 应用运行在InterSystems IRIS中。五个受限工具读取订单、付款记录、付款人历史、证据和规则。本演示在原生工作流中使用已录制的智能体建议，不会把回放伪装成实时模型推理。


### S03  00:40 to 01:00

Visual: Actual missing evidence and stored destination on the new case; no missing-recipient case footage or new live inference claim.

Mode caption (EN): RECORDED proposal. Native IRIS workflow. Synthetic effects.

On screen (EN): Unknown stays unknown.

Narration en: Two payments of eighty-four reais were observed for one order. The proposal requests human review. Missing delivery evidence remains explicitly missing in the sealed context. The refund destination comes from the stored case record, not an instruction in a customer message.

Narration pt-BR: Foram observados dois pagamentos de oitenta e quatro reais para um pedido. A proposta solicita revisão humana. A ausência do comprovante de entrega fica registrada no contexto selado. O destino vem do registro armazenado do caso, não de uma instrução na mensagem do cliente.

Narration es: Se observaron dos pagos de ochenta y cuatro reales para un pedido. La propuesta solicita revisión humana. La falta del comprobante de entrega queda registrada en el contexto sellado. El destino procede del registro almacenado del caso, no de instrucciones del cliente.

Narration zh-CN: 同一订单出现了两笔八十四雷亚尔的付款，建议要求人工审核。缺失的送达凭证会明确保留在封存上下文中。退款目标来自已存储的案件记录，而不是客户消息中的指令。


### S04  01:00 to 01:24

Visual: One authentic approval of new video-flow:5751dd54 and actual test-refund:460,84BRL; prior456/340 preserved.

Mode caption (EN): RECORDED proposal. Native IRIS workflow. Synthetic effects.

On screen (EN): One approval. One synthetic effect.

Narration en: Now an authenticated test reviewer checks the amount, destination, and exact decision commitment. One approval is recorded, sealed, and linked to a single-use permit. The test ledger executes once. Here is the actual intact receipt from this new demonstration case. No real money moved.

Narration pt-BR: Agora, um revisor de teste autenticado confere o valor, o destino e o compromisso exato da decisão. Uma aprovação é registrada, selada e vinculada a uma permissão de uso único. O livro de testes executa uma vez. Este é o recibo real e íntegro do novo caso de demonstração. Nenhum dinheiro real foi movimentado.

Narration es: Un revisor de prueba autenticado comprueba el importe, el destino y el compromiso exacto de la decisión. Una aprobación queda registrada, sellada y vinculada a un permiso de un solo uso. El libro de pruebas ejecuta una vez. Este es el recibo íntegro del nuevo caso. No se movió dinero real.

Narration zh-CN: 已认证的测试审核人检查金额、目标和决策摘要。一次批准被记录并封存，再绑定到一次性许可。测试账本只执行一次。这是本次新演示案件的完整收据，没有发生真实资金转移。


### S05  01:24 to 01:46

Visual: Edit one cent in a COPY of the new sealed decision record; actual verification tampered then restored intact. Stored record unchanged.

Mode caption (EN): RECORDED proposal. Native IRIS workflow. Synthetic effects.

On screen (EN): Change the copy. Verification fails.

Narration en: Change one cent in a copy of the sealed decision. The verifier detects the mismatch. Restore the original copy: intact. The stored record is untouched. These are local seals; they do not protect against an administrator rewriting the database. External anchoring is outside this release.

Narration pt-BR: Altere um centavo em uma cópia da decisão selada. O verificador detecta a diferença. Restaure a cópia original: íntegra. O registro armazenado não foi alterado. Os selos são locais e não protegem contra um administrador que reescreva o banco. A ancoragem externa fica fora desta versão.

Narration es: Cambia un céntimo en una copia de la decisión sellada. El verificador detecta la diferencia. Restaura la copia original: íntegra. El registro almacenado sigue intacto. Los sellos locales no protegen frente a un administrador que reescriba la base. El anclaje externo queda fuera de esta versión.

Narration zh-CN: 在封存决策的副本中改动一分钱，验证器就会发现不一致。恢复原始副本后，验证通过。存储记录没有被修改。这些是本地封印，不能防止管理员重写数据库；本版本不包含外部锚定。


### S06  01:46 to 02:06

Visual: Actual timeline and receipts on the same completed case after the replay-loading race fix. No additional approval or effect.

Mode caption (EN): RECORDED proposal. Native IRIS workflow. Synthetic effects.

On screen (EN): Native workflow. Inspectable history.

Narration en: Intake, decision processing, agent tools, Witness, human Workflow, and the test ledger form one native interoperability path. The console preserves the actual tool outputs and the event timeline. Each effect can be traced back to its evidence, decision, and sealed approval.

Narration pt-BR: Entrada, processamento da decisão, ferramentas do agente, Witness, Workflow humano e livro de testes formam um caminho nativo de interoperabilidade. O console preserva as saídas reais das ferramentas e a linha do tempo. Cada efeito pode ser rastreado até suas evidências, decisão e aprovação selada.

Narration es: Entrada, procesamiento, herramientas del agente, Witness, Workflow humano y libro de pruebas forman un flujo nativo de interoperabilidad. El panel conserva las salidas reales de las herramientas y la cronología. Cada efecto se puede rastrear hasta sus pruebas, decisión y aprobación sellada.

Narration zh-CN: 消息接入、决策处理、智能体工具、Witness、人工Workflow和测试账本组成原生互操作流程。控制台保留实际工具输出和事件时间线。每次测试执行都可追溯到证据、决策以及封存的批准。


### S07  02:06 to 02:29

Visual: Real browser navigation through a review document compiled from published frozen-round JSON;14=10regressions+4controls,6effects,8negativezero,1dangerous proposal contained. Not the product UI or new model run.

Mode caption (EN): PAST LIVE EVALUATION. Frozen cohorts, not a new run.

On screen (EN): Show failures. Measure the protection.

Narration en: Live model evaluation was run separately, with four frozen rounds and earlier failures retained. The latest fourteen cases include ten regressions and four prospective controls. Six legitimate effects completed; eight negatives produced none. One dangerous raw proposal was contained by server checks. This is bounded evidence, not a claim of perfect AI.

Narration pt-BR: A avaliação com modelo ao vivo foi feita separadamente, em quatro rodadas congeladas, preservando as falhas anteriores. Os quatorze casos mais recentes incluem dez regressões e quatro controles prospectivos. Seis efeitos legítimos foram concluídos; oito negativos não geraram efeito. Uma proposta bruta perigosa foi contida no servidor. Isso é evidência limitada, não uma promessa de IA perfeita.

Narration es: La evaluación del modelo en vivo se hizo por separado: cuatro rondas congeladas, con los fallos anteriores conservados. Los catorce casos más recientes incluyen diez regresiones y cuatro controles prospectivos. Se completaron seis efectos legítimos y ocho negativos no generaron ninguno. El servidor contuvo una propuesta peligrosa. Es evidencia limitada, no una promesa de IA perfecta.

Narration zh-CN: 实时模型评估单独进行，共四轮，测试方案预先冻结，并保留早期失败。最近十四个案例包含十个回归案例和四个前瞻控制案例。六个合法测试执行成功，八个负面案例没有执行；一个危险原始建议被服务器检查阻止。这是范围有限的证据，不代表人工智能绝对可靠。


### S08  02:29 to 02:48

Visual: Real navigation through the same review document: installation qualifications, separate vendor image, MIT source, synthetic-voice credit. No fabricated terminal or fresh installation run.

Mode caption (EN): DOCUMENTED TEST RESULTS. Synthetic narration, not Rafael.

On screen (EN): Evidence. Review. One effect.

Narration en: Cold installation, lifecycle, and native package installation were tested. A fresh IPM bootstrap also passed, with its remaining repeatability limits documented. The source is MIT licensed; the vendor image is obtained separately. Proof Before Pay: evidence, review, one synthetic effect.

Narration pt-BR: A instalação do zero, o ciclo de vida e o pacote nativo foram testados. A inicialização do IPM em volume novo também passou, com seus limites de repetibilidade documentados. O código tem licença MIT; a imagem do fornecedor é obtida separadamente. Proof Before Pay: evidência, revisão, um efeito sintético.

Narration es: Se probaron la instalación desde cero, el ciclo de vida y el paquete nativo. El arranque de IPM en un volumen nuevo también pasó, con sus límites de repetibilidad documentados. El código tiene licencia MIT; la imagen del proveedor se obtiene por separado. Proof Before Pay: pruebas, revisión y un efecto sintético.

Narration zh-CN: 已测试全新安装、生命周期和原生软件包安装。新卷上的IPM初始化也已通过，其可重复性限制仍明确记录。源代码采用MIT许可证，厂商镜像需单独获取。Proof Before Pay：证据、审核、一次合成资金执行。

## Description block (EN)

Proof Before Pay: actual native InterSystems IRIS workflow, a recorded agent proposal, one authenticated synthetic reviewer approval, and one synthetic test effect. Separate frozen live evaluation is explicitly labelled. Local seals do not prevent administrator database rewrites; external anchoring is outside this release. Synthetic narration, not Rafael’s voice. English master with Portuguese, Spanish and Mandarin alternate narration and closed captions. Source MIT; vendor image obtained separately. Submission is pending Rafael approval.

## Scene checklist

- S01-S04: actual new recorded agent-path case video-flow:5751dd54; no rules refund relabelled or live inference simulated.
- S03: actual missing delivery evidence and stored target on the same recorded case; no v4live or unfilmed negative-case scene claim.
- S04: exactly one authenticated synthetic review, receipt460 and sealed458<authorized459<executed460. Historical340/456 are not reset or reapproved.
- S05: tampered copy then restored intact; stored native record unchanged.
- S06: actual console timeline and tool outputs after the accepted replay-loading correction; no Portal trace footage claimed.
- S07: browser document compiled from frozen benchmark JSON, explicit prior-evaluation label; no new model run or population-accuracy claim.
- S08: documented installation limits, separate vendor image and synthetic narration credit. Public report footer contains no internal submission-approval discussion.
- Native product labels recorded/sandbox/test ledger remain visible; explanatory report remains visibly identified as a review document.
- All four approved4.1.1 AAC and CC packet streams are copied unchanged; no CC regeneration or fresh TTS for this visual correction.
