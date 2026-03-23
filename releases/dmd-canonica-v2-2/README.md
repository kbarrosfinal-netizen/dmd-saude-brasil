# Publicação oficial — Base Canônica DMD Saúde Brasil v2.2

**Data de publicação:** 2026-03-20  
**Status:** baseline operacional publicada  
**Repositório:** https://github.com/kbarrosfinal-netizen/dmd-saude-brasil

## Escopo desta publicação
Esta release consolida a **base canônica municipal v2.2** do projeto DMD Saúde Brasil com espinha oficial de **5.570 municípios IBGE**, trilha de auditoria dos remapeamentos validados, materialização dos aliases homologados e pacote completo de arquivos de apoio para operação, revisão e governança.

## Resultado executivo
- **5.570 municípios oficiais** na base final.
- **5.570 códigos IBGE únicos**.
- **0 duplicidades de IBGE**.
- **5.530 municípios com correspondência materializada em critério estrito**.
- **5.541 municípios validados em critério gerencial**.
- **40 municípios oficiais sem correspondência segura**.
- **28 pendências remanescentes para decisão manual**.
- **12 aliases validados materializados/confirmados na v2.2**.
- **1 homologação manual aplicada e materializada:** São Bento do Uma → São Bento do Una (PE, IBGE 2613008).

## Nota metodológica executiva
A construção da v2.2 partiu da espinha oficial de municípios do IBGE e da base canônica já reconciliada nas etapas anteriores. O processo seguiu uma lógica conservadora de integração:

1. **Reconciliar por evidência forte** quando havia correspondência exata por nome oficial ou código IBGE.
2. **Separar casos ambíguos** para trilha de validação manual, evitando remapeamento forçado quando a evidência era fraca, contraditória ou com risco de atribuição indevida.
3. **Homologar manualmente apenas os casos com justificativa robusta**, como São Bento do Uma → São Bento do Una.
4. **Materializar aliases validados** diretamente na linha oficial do município destino, preservando a trilha de origem sem inflar artificialmente a cobertura estrita.
5. **Manter quarentena auditável** para as pendências remanescentes, registradas em arquivos próprios.

## Interpretação das métricas
Há duas leituras de cobertura nesta release:

- **Critério estrito/materializado:** conta apenas municípios oficiais cuja linha final na base já possui correspondência materializada. Nessa leitura, a v2.2 chega a **5.530**.
- **Critério gerencial/validado:** soma também os **12 aliases já validados** na trilha de decisão, mesmo quando eles apontam para municípios que já estavam cobertos na espinha oficial. Nessa leitura, a v2.2 chega a **5.541**.

Essas métricas não se contradizem: elas medem coisas diferentes. A primeira mede cobertura efetivamente materializada por linha oficial; a segunda mede volume de decisões já validadas para uso executivo.

## Homologação manual destacada
A release incorpora a homologação manual de **São Bento do Uma → São Bento do Una (PE)**, com reaproveitamento dos atributos disponíveis na linha v1 de origem. A linha oficial final de São Bento do Una permanece marcada como homologada manualmente e contém os principais atributos operacionais, incluindo população, leitos SUS e score_v3.

## Aliases materializados na v2.2
### Novamente materializados nesta versão
- Heliolândia → Heliópolis
- Barão de Monte Alto → Barão do Monte Alto
- Brasópolis → Brazópolis
- Cachoeira Dourada de Minas → Cachoeira Dourada
- Dom Expedito Lins → Dom Expedito Lopes
- Vila Alta → Alto Paraíso
- Augusto Severo → Campo Grande

### Já materializados e confirmados
- Ibicoa → Ibicoara
- Governador Edson Lobão → Governador Edison Lobão
- Belo do Piauí → Belém do Piauí
- Caicaú → Caicó
- Cruzeiro do Nordeste → Cruzeiro do Sul

## Conteúdo desta pasta
- `dmd_base_municipal_canonica_v2_2.csv` — base municipal principal.
- `dmd_base_canonica_integrada_v2_2.xlsx` — workbook integrado para uso operacional e revisão.
- `dmd_base_uf_canonica_v2_2.csv` — resumo por UF.
- `dmd_aliases_materializados_12_v2_2.csv` — trilha específica dos 12 aliases validados.
- `dmd_validacao_41_pendencias_v2_2.csv` — quadro completo das 41 validações e seu status de materialização.
- `dmd_pendencias_remanescentes_28_v2_2.csv` — pendências ainda abertas.
- `dmd_proposta_decisao_manual_29_casos_v2_2.csv` — proposta consolidada de decisão manual.
- `dmd_resumo_v2_2.json` — sumário executivo em JSON.

## Baseline operacional
Esta release deve ser tratada como a **baseline operacional v2.2** para análises, exportações, validação executiva e continuidade do saneamento. Recomenda-se que qualquer nova rodada de reconciliação parta desta versão, preservando:

- a espinha oficial de 5.570 municípios;
- a separação explícita entre correspondência estrita e validação gerencial;
- a trilha auditável dos aliases e homologações manuais;
- a quarentena formal das pendências remanescentes.

## Próximo passo recomendado
A próxima evolução natural é uma **v2.3** focada nas **28 pendências remanescentes**, priorizadas por UF e por força de evidência, para tentar elevar a cobertura estrita acima de 5.530 sem comprometer a integridade do cadastro oficial.
