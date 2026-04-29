from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from app.models.models import Resultados, Indicadores, BancoDeQuestoes
from app.services.calculator import processar_indicador

async def processar_resultado_service(db: AsyncSession, resultado_id: int):
    # Fetch result with bancoDeQuestoes
    stmt = select(Resultados).where(Resultados.id == resultado_id).options(joinedload(Resultados.banco_de_questoes))
    result = await db.execute(stmt)
    resultado = result.scalar_one_or_none()
    
    if not resultado or resultado.erro:
        return None
    
    # Process indicator using the calculator
    indicador_valor = await processar_indicador(
        resultado.tipo_resultado, 
        resultado.json_resultado, 
        resultado.banco_de_questoes.gabarito
    )
    
    # Create or update indicator
    indicador = Indicadores(
        indicador=indicador_valor,
        modelo_id=resultado.modelo_id,
        metrica_id=resultado.banco_de_questoes.metrica_id
    )
    
    db.add(indicador)
    await db.commit()
    return indicador
