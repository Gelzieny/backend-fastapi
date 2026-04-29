from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List
from app.db.session import get_db
from app.models.models import Provedores, Modelos, Metricas, BancoDeQuestoes
from app.schemas import schemas
from app.core.config import settings
from app.api.endpoints import charts
from app.websocket.manager import manager
from app.workers.benchmark_tasks import run_model_benchmark

class UnicodeJSONResponse(JSONResponse):
    def render(self, content: any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

app = FastAPI(title=settings.PROJECT_NAME, default_response_class=UnicodeJSONResponse)

app.include_router(charts.router, prefix="/api/charts", tags=["charts"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    return {"message": "Benchmark IA API is running"}

@app.get("/api/provedores", response_model=List[schemas.Provedor])
async def get_provedores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Provedores))
    return result.scalars().all()

@app.get("/api/modelos", response_model=List[schemas.Modelo])
async def get_modelos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Modelos).order_by(Modelos.id))
    return result.scalars().all()

@app.post("/api/modelos/modelo")
async def post_modelo(data: dict, db: AsyncSession = Depends(get_db)):
    modelo = Modelos(nome=data['modelo'], provedor_id=data['provedor'])
    db.add(modelo)
    await db.commit()
    await db.refresh(modelo)
    # Trigger celery task
    run_model_benchmark.delay([modelo.id])
    return {"id": modelo.id}

@app.put("/api/modelos/modelo")
async def put_modelo(data: dict, db: AsyncSession = Depends(get_db)):
    run_model_benchmark.delay([data['id']])
    return {"status": "reprocessing"}

@app.delete("/api/modelos/modelo")
async def delete_modelo(data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Modelos).filter(Modelos.id == data['id']))
    modelo = result.scalar_one_or_none()
    if modelo:
        await db.delete(modelo)
        await db.commit()
    return {"status": "deleted"}

@app.get("/api/banco-questoes")
async def get_banco_questoes(db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    stmt = select(BancoDeQuestoes).options(joinedload(BancoDeQuestoes.metrica))
    result = await db.execute(stmt)
    questoes = result.scalars().all()
    
    return [
        {
            "id": q.id,
            "metrica_id": q.metrica_id,
            "tipo_metrica": q.metrica.tipo.value,
            "pergunta": q.pergunta,
            "gabarito": q.gabarito
        } for q in questoes
    ]

@app.get("/api/db/setup")
async def setup_database():
    from app.db.init_db import init_db
    from app.db.seed import seed_data
    try:
        print("Iniciando inicialização do banco de dados via API...")
        await init_db()
        print("Iniciando seeding do banco de dados via API...")
        await seed_data()
        return {"status": "success", "message": "Banco de dados inicializado e populado com sucesso."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}

@app.get("/api/debug/run-benchmark")
async def debug_run_benchmark(modelo_id: int):
    from app.workers.benchmark_tasks import _run_model_benchmark_async
    try:
        await _run_model_benchmark_async([modelo_id])
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/tabela")
async def get_tabela(db: AsyncSession = Depends(get_db)):
    # Subquery for calculating average scores per model and metric type
    # Using CASE to map TipoMetrica to table columns
    stmt = text("""
        SELECT 
            m.id, 
            m.nome as nome_modelo,
            AVG(CASE WHEN met.tipo = 'CompreensaoTextual' THEN ind.indicador ELSE NULL END) as compreensaotextualmetrica,
            AVG(CASE WHEN met.tipo = 'ClarezaResposta' THEN ind.indicador ELSE NULL END) as clarezarespostametrica,
            AVG(CASE WHEN met.tipo = 'TesteDoEmbed' THEN ind.indicador ELSE NULL END) as vibecode, -- Mapping as per original requirements
            AVG(CASE WHEN met.tipo = 'DireitoAdministrativo' THEN ind.indicador ELSE NULL END) as direitometrica,
            AVG(CASE WHEN met.tipo = 'Matematica' THEN ind.indicador ELSE NULL END) as matematica,
            AVG(CASE WHEN met.tipo = 'RaciocinioLogico' THEN ind.indicador ELSE NULL END) as raciociniometrica
        FROM modelos m
        LEFT JOIN indicadores ind ON m.id = ind.modelo_id
        LEFT JOIN metricas met ON ind.metrica_id = met.id
        GROUP BY m.id, m.nome
        ORDER BY m.id
    """)
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "id": r.id,
            "nome_modelo": r.nome_modelo,
            "compreensaotextualmetrica": round(float(r.compreensaotextualmetrica or 0), 2),
            "qualidaderesposta": 0, # This seems to be a placeholder in the original
            "clarezarespostametrica": round(float(r.clarezarespostametrica or 0), 2),
            "direitometrica": round(float(r.direitometrica or 0), 2),
            "matematica": round(float(r.matematica or 0), 2),
            "raciociniometrica": round(float(r.raciociniometrica or 0), 2),
            "vibecode": round(float(r.vibecode or 0), 2)
        } for r in rows
    ]

@app.get("/api/contar-indicadores")
async def contar_indicadores(db: AsyncSession = Depends(get_db)):
    stmt = text("""
        SELECT 
            met.tipo,
            COUNT(ind.id) as total
        FROM metricas met
        LEFT JOIN indicadores ind ON met.id = ind.metrica_id
        GROUP BY met.tipo
    """)
    result = await db.execute(stmt)
    return [dict(row._mapping) for row in result]

@app.get("/api/contar-clareza")
async def contar_clareza(db: AsyncSession = Depends(get_db)):
    stmt = text("""
        SELECT 
            m.nome as modelo,
            AVG(ind.indicador) as media
        FROM modelos m
        JOIN indicadores ind ON m.id = ind.modelo_id
        JOIN metricas met ON ind.metrica_id = met.id
        WHERE met.tipo = 'ClarezaResposta'
        GROUP BY m.nome
    """)
    result = await db.execute(stmt)
    return {"resultadoModelos": [dict(row._mapping) for row in result]}
