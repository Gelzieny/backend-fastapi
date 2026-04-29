from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()

def get_standard_chart_query(metrica_tipo: str):
    return text(f"""
    with total_metric as (
    SELECT met.id, count(*) as total
    FROM indicadores as ind
    INNER JOIN metricas as met on met.id = ind.metrica_id
    INNER JOIN modelos AS mls on ind.modelo_id = mls.id
    where tipo = '{metrica_tipo}'
    GROUP BY 1
    ),
    tokens as (
    SELECT
    res.modelo_id AS modelo_id,
    ROUND(AVG(res.input_tokens),2) as tokensentradas,
    ROUND(AVG(res.output_tokens),2) as tokensaida,
    ROUND(AVG(res.total_tokens),2) as tokenstotais
    FROM resultados AS res
    where tipo_resultado = '{metrica_tipo}'
    GROUP BY 1)

    SELECT met.tipo, mls.nome, ind.indicador, tokensentradas, tokensaida, tokenstotais, ROUND((CAST(count(ind.indicador) AS DECIMAL) / MAX(td.total))*100,2)  as count 
    FROM indicadores as ind
    INNER JOIN metricas as met on met.id = ind.metrica_id
    INNER JOIN modelos AS mls on ind.modelo_id = mls.id
    INNER JOIN total_metric td on td.id = met.id
    INNER JOIN tokens t on t.modelo_id = ind.modelo_id

    where tipo = '{metrica_tipo}'
    GROUP BY 1,2,3,4,5,6;
    """)

@router.get("/alucinacao")
async def get_alucinacao(db: AsyncSession = Depends(get_db)):
    # Query for totalErro
    total_erro_sql = text("""
    WITH TotalDados AS (
        SELECT
        bdq.metrica_id,
        res.modelo_id,
        COUNT(*) AS total_geral
        FROM resultados AS res
        INNER JOIN banco_de_questoes AS bdq 
         ON res.banco_de_questoes_id = bdq.id
		WHERE 
		res.tipo_resultado in ('ClarezaResposta', 'CompreensaoTextual') 
        GROUP BY 1,2
      ),
 	TotalErros AS (
        SELECT
        bdq.metrica_id,
        res.modelo_id,
        COUNT(*) AS total_geral_erros
        FROM resultados AS res
        INNER JOIN banco_de_questoes AS bdq 
          ON res.banco_de_questoes_id = bdq.id
        WHERE
          regexp_replace(lower(trim(res.json_resultado->>'resposta')), '[^a-z0-9]', '', 'g') !=
          regexp_replace(lower(trim(bdq.gabarito->>'resposta')), '[^a-z0-9]', '', 'g')
          GROUP BY 1,2
      ),
    tabalucinacao AS (
      SELECT 
        bdq.metrica_id,
        res.modelo_id,
        COUNT(*)::integer AS totalucinacao
      FROM resultados AS res
      INNER JOIN banco_de_questoes AS bdq ON res.banco_de_questoes_id = bdq.id
      INNER JOIN metricas as mt on bdq.metrica_id = mt.id
      WHERE
        (
          mt.tipo = 'ClarezaResposta' AND
          NOT LOWER(TRIM(res.json_resultado->>'resposta')) IN ('1', '2', '3', '4', '5')
        )
        OR
        (
          mt.tipo = 'CompreensaoTextual' AND
          NOT regexp_replace(lower(trim(res.json_resultado->>'resposta')), '[^a-z0-9]', '', 'g')  IN (
            'contradio', 'implicao'
          )
        )
      GROUP BY 
        bdq.metrica_id, res.modelo_id)
      SELECT 
      td.metrica_id,
      td.modelo_id,
      mls.nome as modelo,
      mt.tipo,
      coalesce(((e.totalucinacao::float / td.total_geral) * 100)::NUMERIC(10, 2),0)  AS porcentagem_alucinacao,
  	  coalesce((((te.total_geral_erros::float - COALESCE(e.totalucinacao::float, 0) ) / td.total_geral) * 100)::NUMERIC(10, 2),0)  AS porcentagem_erros
      FROM TotalDados td
      inner join metricas as mt on td.metrica_id = mt.id
      INNER JOIN modelos AS mls on td.modelo_id = mls.id
      LEFT JOIN TotalErros te on td.metrica_id = te.metrica_id and td.modelo_id = te.modelo_id
	  LEFT JOIN tabalucinacao e  on td.metrica_id = e.metrica_id and td.modelo_id = e.modelo_id;
    """)
    
    # Query for totalAlucinacao
    total_alucinacao_sql = text("""
    WITH TotalErros AS (
        SELECT
        bdq.metrica_id,
        res.modelo_id,
        COUNT(*) AS total_geral_erros
        FROM resultados AS res
        INNER JOIN banco_de_questoes AS bdq 
          ON res.banco_de_questoes_id = bdq.id
        WHERE
          regexp_replace(lower(trim(res.json_resultado->>'resposta')), '[^a-z0-9]', '', 'g') !=
          regexp_replace(lower(trim(bdq.gabarito->>'resposta')), '[^a-z0-9]', '', 'g')
          GROUP BY 1,2
      ),
    tabalucinacao AS (
      SELECT 
        bdq.metrica_id,
        res.modelo_id,
        COUNT(*)::integer AS totalucinacao
      FROM resultados AS res
      INNER JOIN banco_de_questoes AS bdq ON res.banco_de_questoes_id = bdq.id
      INNER JOIN metricas as mt on bdq.metrica_id = mt.id
      WHERE
        (
          mt.tipo = 'ClarezaResposta' AND
          NOT LOWER(TRIM(res.json_resultado->>'resposta')) IN ('1', '2', '3', '4', '5')
        )
        OR
        (
          mt.tipo = 'CompreensaoTextual' AND
          NOT regexp_replace(lower(trim(res.json_resultado->>'resposta')), '[^a-z0-9]', '', 'g')  IN (
            'contradio', 'implicao'
          )
        )
      GROUP BY 
        bdq.metrica_id, res.modelo_id)
      SELECT 
      e.metrica_id,
      e.modelo_id,
      mls.nome as modelo,
      mt.tipo,
      e.totalucinacao::integer,
      te.total_geral_erros::integer,
      ((e.totalucinacao::float / te.total_geral_erros) * 100)::NUMERIC(10, 2)  AS porcentagem_erro
      FROM tabalucinacao e
      inner join metricas as mt on e.metrica_id = mt.id
      INNER JOIN modelos AS mls on e.modelo_id = mls.id
      LEFT JOIN TotalErros te on e.metrica_id = te.metrica_id and e.modelo_id = te.modelo_id;
    """)

    res_erro = await db.execute(total_erro_sql)
    res_alucinacao = await db.execute(total_alucinacao_sql)
    
    return {
        "totalErro": [dict(row._mapping) for row in res_erro],
        "totalAlucinacao": [dict(row._mapping) for row in res_alucinacao]
    }

@router.get("/matematica")
async def get_matematica(db: AsyncSession = Depends(get_db)):
    result = await db.execute(get_standard_chart_query("Matematica"))
    return [dict(row._mapping) for row in result]

@router.get("/direito-adm")
async def get_direito_adm(db: AsyncSession = Depends(get_db)):
    result = await db.execute(get_standard_chart_query("DireitoAdministrativo"))
    return [dict(row._mapping) for row in result]

@router.get("/raciocinio-logico")
async def get_raciocinio_logico(db: AsyncSession = Depends(get_db)):
    result = await db.execute(get_standard_chart_query("RaciocinioLogico"))
    return [dict(row._mapping) for row in result]

@router.get("/vibe-coding")
async def get_vibe_coding(db: AsyncSession = Depends(get_db)):
    result = await db.execute(get_standard_chart_query("VibeCoding"))
    return [dict(row._mapping) for row in result]

@router.get("/embedtest")
async def get_embedtest(db: AsyncSession = Depends(get_db)):
    result = await db.execute(get_standard_chart_query("TesteDoEmbed"))
    return [dict(row._mapping) for row in result]
