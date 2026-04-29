import re
from typing import Any, Dict, Optional
from app.models.models import TipoMetrica, Provider
from app.services.ai_engine import ai_engine

class EvalService:
    @staticmethod
    def _clean_think_tag(text: str) -> str:
        """Removes <think>...</think> tags if present."""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    async def get_ai_response(self, metrica: TipoMetrica, provider: str, model_name: str, context: Any) -> Dict[str, Any]:
        if metrica == TipoMetrica.Matematica:
            return await self._eval_matematica(provider, model_name, context)
        elif metrica == TipoMetrica.CompreensaoTextual:
            return await self._eval_compreensao_textual(provider, model_name, context)
        elif metrica == TipoMetrica.DireitoAdministrativo:
            return await self._eval_direito_administrativo(provider, model_name, context)
        elif metrica == TipoMetrica.RaciocinioLogico:
            return await self._eval_raciocinio_logico(provider, model_name, context)
        elif metrica == TipoMetrica.ClarezaResposta:
            return await self._eval_clareza_resposta(provider, model_name, context)
        elif metrica == TipoMetrica.TesteDoEmbed:
            return await self._eval_teste_do_embed(provider, model_name, context)
        elif metrica == TipoMetrica.VibeCoding:
            return await self._eval_vibe_coding(provider, model_name, context)
        else:
            raise ValueError(f"Métrica {metrica} não suportada para avaliação")

    async def _eval_matematica(self, provider: str, model_name: str, ctx: Any) -> Dict[str, Any]:
        system_prompt = """Solve the following math problem step by step. If you do not know how to solve the problem, your only response should be "I do not know the answer."
Otherwise, provide the solution and ensure the last line of your response is exclusively in the form “ANSWER: $ANSWER” (without quotes), where $ANSWER is the final answer. Do not use a \boxed command."""
        
        user_msg = ctx.get("pergunta")
        res_text = await ai_engine.generate_text(provider, model_name, user_msg, system_prompt)
        res_text = self._clean_think_tag(res_text)
        
        return {
            "resposta": res_text,
            "pergunta": user_msg,
            "modelMetadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}} # Tokens tracking to be improved
        }

    async def _eval_compreensao_textual(self, provider: str, model_name: str, ctx: Any) -> Dict[str, Any]:
        system_prompt = """Sua tarefa é analisar a relação entre a Hipótese e a Premissa.
Classifique cada relação em uma das duas categorias exclusivas:
* implicação: Se a Hipótese for necessariamente verdadeira com base na Premissa.
* contradição: Se a Hipótese for necessariamente falsa ou impossível com base na Premissa.
A sua resposta deverá ser direta, respondendo apenas as palavaras implicação ou contradição"""
        
        user_msg = f"Premissa: {ctx.get('premissa')}\nHipótese: {ctx.get('hipotese')}"
        res_text = await ai_engine.generate_text(provider, model_name, user_msg, system_prompt)
        res_text = self._clean_think_tag(res_text)
        
        return {
            "resposta": res_text,
            "modelMetadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}}
        }

    async def _eval_direito_administrativo(self, provider: str, model_name: str, ctx: Any) -> Dict[str, Any]:
        system_prompt = """Você é um especialista em Direito Administrativo. 
1. Primeira Linha: APENAS "True", "False" ou "Não Sei".
2. A Partir da Segunda Linha: Justificativa jurídica."""
        
        user_msg = f"Frase: {ctx.get('pergunta')}"
        res_text = await ai_engine.generate_text(provider, model_name, user_msg, system_prompt)
        res_text = self._clean_think_tag(res_text)
        
        linhas = res_text.split('\n')
        resposta_final = linhas[0].strip()
        justificativa = '\n'.join(linhas[1:]).strip() if len(linhas) > 1 else res_text
        
        return {
            "pergunta": ctx.get('pergunta'),
            "resposta": resposta_final,
            "justificativa_resposta": justificativa,
            "modelMetadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}}
        }

    # Add other methods (Raciocinio, Clareza, Embed, VibeCoding) similarly...
    async def _eval_raciocinio_logico(self, provider: str, model_name: str, ctx: Any) -> Dict[str, Any]:
        system_prompt = "Resolva o problema de raciocínio lógico passo a passo. A última linha deve ser RESPOSTA: $RESPOSTA"
        user_msg = ctx.get("pergunta")
        res_text = await ai_engine.generate_text(provider, model_name, user_msg, system_prompt)
        res_text = self._clean_think_tag(res_text)
        return {"resposta": res_text, "pergunta": user_msg, "modelMetadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}}}

    async def _eval_clareza_resposta(self, provider: str, model_name: str, ctx: Any) -> Dict[str, Any]:
        system_prompt = "Avalie a clareza da resposta de 1 a 5."
        user_msg = ctx.get("texto")
        res_text = await ai_engine.generate_text(provider, model_name, user_msg, system_prompt)
        res_text = self._clean_think_tag(res_text)
        return {"resposta": res_text, "modelMetadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}}}

    async def _eval_teste_do_embed(self, provider: str, model_name: str, ctx: Any) -> Dict[str, Any]:
        # This one usually involves RAG. Need to implement RAG retrieval logic later.
        system_prompt = "Responda a pergunta baseada no contexto fornecido."
        user_msg = ctx.get("pergunta")
        res_text = await ai_engine.generate_text(provider, model_name, user_msg, system_prompt)
        return {"resposta": res_text, "pergunta": user_msg, "rag": "context_placeholder", "modelMetadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}}}

    async def _eval_vibe_coding(self, provider: str, model_name: str, ctx: Any) -> Dict[str, Any]:
        system_prompt = "Gere apenas o código para resolver o problema."
        user_msg = ctx.get("problema")
        res_text = await ai_engine.generate_text(provider, model_name, user_msg, system_prompt)
        return {"resposta": res_text, "problema": user_msg, "codeError": None, "modelMetadata": {"usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0}}}

eval_service = EvalService()
