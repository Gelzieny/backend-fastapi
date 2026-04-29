import asyncio
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.core.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.models import BancoDeQuestoes, Modelos, Resultados, Indicadores
from app.services.eval_service import eval_service
from app.services.results_service import processar_resultado_service
from app.websocket.manager import manager

async def _processar_questao_logic(questao_id: int, modelo_id: int):
    async with AsyncSessionLocal() as db:
        # 1. Fetch Question and Model
        questao_stmt = select(BancoDeQuestoes).where(BancoDeQuestoes.id == questao_id).options(joinedload(BancoDeQuestoes.metrica))
        modelo_stmt = select(Modelos).where(Modelos.id == modelo_id).options(joinedload(Modelos.provedor))
        
        questao_res = await db.execute(questao_stmt)
        modelo_res = await db.execute(modelo_stmt)
        
        questao = questao_res.scalar_one_or_none()
        modelo = modelo_res.scalar_one_or_none()
        
        if not questao or not modelo:
            return None

        # 2. Get AI Response
        try:
            ai_result = await eval_service.get_ai_response(
                questao.metrica.tipo,
                modelo.provedor.nome.value,
                modelo.nome,
                questao.pergunta
            )
            
            metadata = ai_result.get("modelMetadata", {}).get("usage", {})
            
            # 3. Save Raw Result
            resultado = Resultados(
                tipo_resultado=questao.metrica.tipo,
                json_resultado=ai_result,
                banco_de_questoes_id=questao.id,
                modelo_id=modelo.id,
                input_tokens=metadata.get("inputTokens", 0),
                output_tokens=metadata.get("outputTokens", 0),
                total_tokens=metadata.get("totalTokens", 0)
            )
            db.add(resultado)
            await db.flush() # Get ID
            
            # 4. Process Indicator (Score)
            await processar_resultado_service(db, resultado.id)
            
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            # Save Error Result
            resultado_erro = Resultados(
                tipo_resultado=questao.metrica.tipo,
                json_resultado={},
                erro=True,
                json_erro={"message": str(e)},
                banco_de_questoes_id=questao.id,
                modelo_id=modelo.id,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0
            )
            db.add(resultado_erro)
            await db.commit()
            return False

@celery_app.task(name="app.workers.benchmark_tasks.run_model_benchmark")
def run_model_benchmark(modelo_ids: Optional[List[int]] = None):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # This shouldn't happen in a typical Celery worker, but good for safety
        return loop.create_task(_run_model_benchmark_async(modelo_ids))
    else:
        return loop.run_until_complete(_run_model_benchmark_async(modelo_ids))

async def _run_model_benchmark_async(modelo_ids: Optional[List[int]] = None):
    async with AsyncSessionLocal() as db:
        # 1. Identify pending tasks (similar to mapearQuestoesNaoProcessadas)
        modelos_stmt = select(Modelos)
        if modelo_ids:
            modelos_stmt = modelos_stmt.where(Modelos.id.in_(modelo_ids))
        
        modelos_res = await db.execute(modelos_stmt)
        modelos = modelos_res.scalars().all()
        
        questoes_stmt = select(BancoDeQuestoes.id)
        questoes_res = await db.execute(questoes_stmt)
        all_questao_ids = questoes_res.scalars().all()
        
        for modelo in modelos:
            # Find processed for this model
            processed_stmt = select(Resultados.banco_de_questoes_id).where(Resultados.modelo_id == modelo.id)
            processed_res = await db.execute(processed_stmt)
            processed_ids = processed_res.scalars().all()
            
            pendente = [qid for qid in all_questao_ids if qid not in processed_ids]
            
            total = len(pendente)
            print(f"\n" + "="*50)
            print(f"INICIANDO BENCHMARK: {modelo.nome} (ID: {modelo.id})")
            print(f"Total de questões pendentes: {total}")
            print("="*50 + "\n")

            for index, qid in enumerate(pendente):
                # Fetch question again to show metric type in log
                async with AsyncSessionLocal() as db_log:
                    q_stmt = select(BancoDeQuestoes).where(BancoDeQuestoes.id == qid).options(joinedload(BancoDeQuestoes.metrica))
                    q_res = await db_log.execute(q_stmt)
                    q_obj = q_res.scalar_one_or_none()
                    tipo_metrica = q_obj.metrica.tipo.value if q_obj else "Desconhecido"

                print(f"[{index+1}/{total}] [{tipo_metrica}] Processando questão ID: {qid}...")
                
                try:
                    success = await _processar_questao_logic(qid, modelo.id)
                    if success:
                        print(f"  ✅ SUCESSO: Questão {qid}")
                    else:
                        print(f"  ❌ FALHA (Lógica): Questão {qid}")
                except Exception as e:
                    print(f"  🚨 ERRO CRÍTICO na Questão {qid} ({tipo_metrica}): {str(e)}")
                    import traceback
                    traceback.print_exc()
                
                # Notify progress via WebSocket
                progress_msg = {
                    "type": "PROGRESS",
                    "modelo": modelo.nome,
                    "modeloId": modelo.id,
                    "current": index + 1,
                    "total": total,
                    "percentage": round(((index + 1) / total) * 100, 2)
                }
                # Note: manager.broadcast is async. 
                # In a real worker environment, you might use Redis PubSub to notify the main app, 
                # which then broadcasts via WS. For now, we call broadcast directly.
                await manager.broadcast(progress_msg)
                
        await manager.broadcast({"type": "FINISHED", "message": "Benchmark completed"})
