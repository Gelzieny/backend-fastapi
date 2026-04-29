import re
import os
import json
from typing import Any, Dict, Optional
from app.models.models import TipoMetrica
from app.services.ai_engine import ai_engine

def cast_first_char(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r'\d', text)
    if match:
        return int(match.group())
    return None

async def compreensao_textual_engine(output: Dict[str, Any], gabarito: Dict[str, Any]) -> int:
    regex = re.compile(r'[^\w\s]')
    def clean(s: Optional[str]) -> str:
        if not s: return ""
        return regex.sub("", s.lower()).strip()
    
    out_res = clean(output.get("resposta"))
    gab_res = clean(gabarito.get("resposta"))
    
    return 100 if out_res == gab_res else 0

async def clareza_resposta_engine(output: Dict[str, Any], gabarito: Dict[str, Any]) -> int:
    out_val = cast_first_char(str(output.get("resposta", "")))
    gab_val = gabarito.get("resposta")
    
    return 100 if out_val == gab_val else 0

async def _llm_evaluation(prompt: str, system_prompt: Optional[str] = None) -> int:
    provider = os.getenv("EMBED_TEST_PROVIDER", "gemini")
    model = os.getenv("EMBED_TEST_MODEL", "gemini-1.5-flash")
    
    schema = {
        "type": "object",
        "properties": {
            "pontuacaoGeral": {
                "type": "integer",
                "minimum": 0,
                "maximum": 6,
                "description": "Pontuação geral da resposta"
            }
        },
        "required": ["pontuacaoGeral"]
    }
    
    res = await ai_engine.generate_structured_output(provider, model, prompt, schema, system_prompt)
    return res.get("pontuacaoGeral", 0)

async def teste_matematica_engine(output: Dict[str, Any], gabarito: Dict[str, Any]) -> int:
    prompt = f"""
You are a math expert, and your task is to evaluate the quality of the response provided by another AI model for a mathematical problem. The correct answer key for comparison is provided in the **gabarito** field.

Analyze the LLM's response based on the following criteria:
1. Final Answer Correctness: Is the answer in the ANSWER: line mathematically correct? Compare it with the value in the gabarito field.
2. Step-by-Step Correction: Are the reasoning and intermediate calculations correct, and do they logically lead to the final answer?
3. Format Compliance: Does the response strictly follow the requested formatting rules (a step-by-step explanation and the ANSWER: $ANSWER line as the very last line)?

  **[QUESTION]**
  {output.get('pergunta')}
  **[TEMPLATE]**
  {gabarito.get('gabarito')}
  **[ANSWER]**
  {output.get('resposta')}
    """
    return await _llm_evaluation(prompt)

async def direito_administrativo_engine(output: Dict[str, Any], gabarito: Dict[str, Any]) -> int:
    prompt = f"""
Você é um especialista em Direito Administrativo, com conhecimento profundo da doutrina, jurisprudência e legislação brasileira. Sua tarefa é avaliar a resposta de um modelo de IA com base em um gabarito.

**Critérios de Avaliação (pontuação de 0 a 3):**
- (0) Errou: quando a resposta objetiva ("True" ou "False") não corresponde ao gabarito.
- (1) Acertou: quando a resposta objetiva corresponde ao gabarito **e** a justificativa é juridicamente correta (sem contradições, invenções ou distorções).
- (2) Não Sei: quando a resposta objetiva for "Não Sei" **e** a justificativa confirmar que o modelo não sabe ou se recusa a responder.
- (3) Alucinação: em três situações
   a) quando a resposta objetiva for "True" ou "False", mas a justificativa disser que não sabe (contradição);  
   b) quando a resposta objetiva for "Não Sei", mas a justificativa tentar explicar algo referente a questão;  
   c) quando o modelo inventar leis, regras, jurisprudência ou fundamentos inexistentes — mesmo que acerte a resposta objetiva.

**INFORMAÇÕES PARA AVALIAÇÃO:**

**[PERGUNTA ORIGINAL]**
{output.get('pergunta')}

**[GABARITO - RESPOSTA CORRETA]**
{gabarito.get('gabarito')}

**[GABARITO - JUSTIFICATIVA CORRETA]**
{gabarito.get('justificativa')}

**[RESPOSTA DO MODELO AVALIADO]**
{output.get('resposta')}

**[JUSTIFICATIVA DO MODELO AVALIADO]**
{output.get('justificativa_resposta')}
    """
    return await _llm_evaluation(prompt)

async def teste_raciocinio_engine(output: Dict[str, Any], gabarito: Dict[str, Any]) -> int:
    prompt = f"""
Você é um especialista em raciocínio lógico e sua tarefa é avaliar a qualidade da resposta fornecida por outro modelo de IA para um problema lógico. A resposta correta para comparação é fornecida no campo gabarito.

Analise a resposta do LLM com base nos seguintes critérios:
1. Correção da Resposta Final: A resposta na linha RESPOSTA: está logicamente correta? Compare-a com o valor no campo gabarito.
2. Correção do Passo a Passo: A linha de raciocínio está correta e levam logicamente à resposta final?
3. Conformidade com o Formato: A resposta segue estritamente as regras de formatação solicitadas (uma explicação passo a passo e a linha RESPOSTA: $RESPOSTA como a última linha)?

  **[QUESTION]**
  {output.get('pergunta')}
  **[TEMPLATE]**
  {gabarito.get('gabarito')}
  **[ANSWER]**
  {output.get('resposta')}
    """
    return await _llm_evaluation(prompt)

async def teste_do_embed_engine(output: Dict[str, Any], gabarito: Dict[str, Any]) -> int:
    system_prompt = """
# Persona e Objetivo
Você é um LLM Avaliador Sênior, especialista em análise de respostas de modelos de linguagem e em serviços públicos do governo de Goiás. Sua principal tarefa é avaliar a qualidade e a precisão da resposta de um outro modelo de IA, que utiliza a técnica de RAG (Retrieval-Augmented Generation). Sua avaliação deve ser estritamente baseada na relação entre a Pergunta, o Contexto Recuperado e a Resposta do Modelo. Você NÃO deve usar seu conhecimento externo.

# Critérios de Avaliação Detalhados (Pontuação de 0 a 6)
- **PONTUAÇÃO 0 - Alucinação Grave**
- **PONTUAÇÃO 1 - Contradição Grave**
- **PONTUAÇÃO 2 - Ruim / Erro Factual**
- **PONTUAÇÃO 3 - Regular**
- **PONTUAÇÃO 4 - Bom / Resposta Fiel**
- **PONTUAÇÃO 5 - Excelente / Síntese Útil**
- **PONTUAÇÃO 6 - Recusa Apropriada**
"""
    prompt = f"""
# DADOS PARA AVALIAÇÃO
## [Contexto Recuperado (RAG)]
```
{output.get('rag')}
```
## [Pergunta do Usuário]
```
{output.get('pergunta')}
```
## [Resposta do Modelo de IA]
```
{output.get('resposta')}
```
    """
    return await _llm_evaluation(prompt, system_prompt)

async def vibe_coding_engine(output: Dict[str, Any], gabarito: Dict[str, Any]) -> int:
    instruction = f"""
Você é um juiz especialista em avaliar a qualidade de código gerado por IA. Sua tarefa é avaliar a resposta de um modelo de IA para um problema de programação.

**Problema:**
{output.get('problema')}

**Gabarito (Solução Correta):**
{gabarito.get('gabarito')}

**Resposta do Modelo:**
{output.get('resposta')}

**Erro de Execução:**
{output.get('codeError')}

**Resumo das Pontuações:**
*   **3 (Alucinou):** A resposta não é um código, ou o código falhou na execução.
*   **2 (Não soube responder):** O modelo explicitamente se recusa a responder.
*   **1 (Acertou):** O código executa sem erros e a lógica resolve o problema corretamente.
*   **0 (Errou):** O código executa sem erros, mas a lógica está incorreta.
    """
    return await _llm_evaluation(instruction)

ENGINE_MAP = {
    TipoMetrica.CompreensaoTextual: compreensao_textual_engine,
    TipoMetrica.ClarezaResposta: clareza_resposta_engine,
    TipoMetrica.TesteDoEmbed: teste_do_embed_engine,
    TipoMetrica.DireitoAdministrativo: direito_administrativo_engine,
    TipoMetrica.Matematica: teste_matematica_engine,
    TipoMetrica.RaciocinioLogico: teste_raciocinio_engine,
    TipoMetrica.VibeCoding: vibe_coding_engine,
}

async def processar_indicador(metrica: TipoMetrica, output: Any, gabarito: Any) -> int:
    engine = ENGINE_MAP.get(metrica)
    if not engine:
        raise ValueError(f"Engine para métrica {metrica} não encontrada")
    return await engine(output, gabarito)
