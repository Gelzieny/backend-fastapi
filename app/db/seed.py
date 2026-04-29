# -*- coding: utf-8 -*-
import asyncio
import json
import os
import sys
from typing import List

# Add the project root to sys.path to allow imports from 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import select, text
from app.db.session import AsyncSessionLocal, engine
from app.models.models import (
    Provedores, Metricas, BancoDeQuestoes, Provider, TipoMetrica, CartaServico, Modelos
)

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../arquivos"))

async def seed_data():
    async with AsyncSessionLocal() as session:
        # Forçar encoding UTF8 na conexão
        await session.execute(text("SET client_encoding TO 'UTF8'"))

        # Limpar Banco de Questões anterior e dados relacionados
        print("Limpando dados anteriores...")
        await session.execute(text("DELETE FROM indicadores"))
        await session.execute(text("DELETE FROM resultados"))
        await session.execute(text("DELETE FROM banco_de_questoes"))
        await session.commit()

        # 1. Provedores
        print("Seeding Provedores...")
        stmt_prov = select(Provedores).where(Provedores.nome == Provider.ollama)
        res_prov = await session.execute(stmt_prov)
        ollama = res_prov.scalar_one_or_none()

        if not ollama:
            ollama = Provedores(nome=Provider.ollama)
            session.add(ollama)
            await session.flush()
            print("Provedor Ollama criado.")

        # 2. Modelos
        print("Seeding Modelos...")
        stmt_mod = select(Modelos).where(Modelos.nome == "llama3", Modelos.provedor_id == ollama.id)
        res_mod = await session.execute(stmt_mod)
        modelo_test = res_mod.scalar_one_or_none()

        if not modelo_test:
            modelo_test = Modelos(nome="llama3", provedor_id=ollama.id)
            session.add(modelo_test)
            await session.flush()
            print("Modelo llama3 criado.")

        # ID do modelo para usar nos mocks
        modelo_id_final = modelo_test.id


        # 2. Metricas
        print("Seeding Metricas...")
        metricas_data = [
            ("Taxa de compreensão", TipoMetrica.CompreensaoTextual),
            ("Clareza da resposta", TipoMetrica.ClarezaResposta),
            ("Teste do embed", TipoMetrica.TesteDoEmbed),
            ("Direito Administrativo", TipoMetrica.DireitoAdministrativo),
            ("Matematica", TipoMetrica.Matematica),
            ("Raciocinio Logico", TipoMetrica.RaciocinioLogico),
            ("Vibe Coding", TipoMetrica.VibeCoding),
        ]
        
        metricas_map = {}
        for nome, tipo in metricas_data:
            # Check if metric already exists
            stmt = select(Metricas).where(Metricas.metricas == nome, Metricas.tipo == tipo)
            existing = await session.execute(stmt)
            m = existing.scalar_one_or_none()
            
            if not m:
                m = Metricas(metricas=nome, tipo=tipo)
                session.add(m)
                await session.flush()
                print(f"Métrica criada: {nome}")
            else:
                print(f"Métrica já existe: {nome}")
            
            metricas_map[tipo] = m.id
        
        await session.commit()

        # 3. Banco de Questoes
        print("Seeding Banco de Questoes...")

        # Compreensão Textual
        with open(f"{DATA_PATH}/compreensao-textual.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data[:10]:
                q = BancoDeQuestoes(
                    metrica_id=metricas_map[TipoMetrica.CompreensaoTextual],
                    pergunta={
                        "categoria": item.get("categoria"),
                        "premissa": item.get("premissa"),
                        "hipotese": item.get("hipotese"),
                        "nivel": item.get("hipotese") # Following seed.ts logic
                    },
                    gabarito={"resposta": item.get("gabarito")}
                )
                session.add(q)

        # Clareza Resposta
        with open(f"{DATA_PATH}/clareza-resposta.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data[:10]:
                q = BancoDeQuestoes(
                    metrica_id=metricas_map[TipoMetrica.ClarezaResposta],
                    pergunta={
                        "texto": item.get("texto"),
                        "gabarito": item.get("gabarito")
                    },
                    gabarito={"resposta": item.get("gabarito")}
                )
                session.add(q)

        # Teste do Embed (perguntas de cartas-servico.json)
        with open(f"{DATA_PATH}/cartas-servico.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            perguntas = data.get("perguntas", [])
            for item in perguntas[:10]:
                q = BancoDeQuestoes(
                    metrica_id=metricas_map[TipoMetrica.TesteDoEmbed],
                    pergunta={"pergunta": item.get("pergunta")},
                    gabarito={}
                )
                session.add(q)

        # Direito Administrativo
        with open(f"{DATA_PATH}/direito-administrativo.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data[:10]:
                q = BancoDeQuestoes(
                    metrica_id=metricas_map[TipoMetrica.DireitoAdministrativo],
                    pergunta={
                        "pergunta": item.get("pergunta"),
                        "nivel": item.get("nivel")
                    },
                    gabarito={
                        "gabarito": item.get("gabarito"),
                        "justificativa": item.get("justificativa")
                    }
                )
                session.add(q)

        # Matematica
        with open(f"{DATA_PATH}/matematica.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data[:10]:
                q = BancoDeQuestoes(
                    metrica_id=metricas_map[TipoMetrica.Matematica],
                    pergunta={
                        "pergunta": item.get("problem"),
                        "nivel": item.get("level"),
                        "tipo": item.get("type")
                    },
                    gabarito={"gabarito": item.get("solution")}
                )
                session.add(q)

        # Raciocinio Logico
        with open(f"{DATA_PATH}/raciocinio-logico.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data[:10]:
                q = BancoDeQuestoes(
                    metrica_id=metricas_map[TipoMetrica.RaciocinioLogico],
                    pergunta={
                        "pergunta": item.get("pergunta"),
                        "nivel": item.get("level")
                    },
                    gabarito={"gabarito": item.get("Gabarito")}
                )
                session.add(q)

        # Vibe Coding
        vc_path = f"{DATA_PATH}/vibecoding/sum-two"
        if os.path.exists(vc_path):
            with open(f"{vc_path}/sum-two-problem.txt", "r", encoding="utf-8") as f:
                problema = f.read()
            # For context/baseScript/gabarito, since they are in a TS file, 
            # I'll just put a placeholder for now as I cannot easily parse TS.
            # In a real migration, we'd extract these to JSON or separate text files.
            q = BancoDeQuestoes(
                metrica_id=metricas_map[TipoMetrica.VibeCoding],
                pergunta={
                    "problema": problema,
                    "contexto": "sumTwoContext",
                    "baseScript": "sumTwoBase",
                    "nivel": "Médio",
                    "tipo": "Matemática"
                },
                gabarito={"gabarito": "sumTwoGabarito"}
            )
            session.add(q)

        await session.commit()
        print("Seed completed successfully.")

        # 4. Mock Resultados e Indicadores para testes de gráficos
        print("Seeding Mock Resultados e Indicadores para todas as métricas...")
        from app.models.models import Resultados, Indicadores
        import random

        # Usar o ID do modelo que foi criado ou já existia
        modelo_id = modelo_id_final 
        
        # Iterar por todas as métricas criadas para gerar dados mock
        for tipo_metrica, metrica_id in metricas_map.items():
            print(f"Gerando dados mock para: {tipo_metrica.value}")
            
            stmt = select(BancoDeQuestoes).where(BancoDeQuestoes.metrica_id == metrica_id)
            res = await session.execute(stmt)
            questoes = res.scalars().all()

            for q in questoes:
                # Criar um resultado mock
                res_mock = Resultados(
                    tipo_resultado=tipo_metrica,
                    json_resultado={"resposta": "Mock Answer", "pergunta": q.pergunta.get("pergunta") or q.pergunta.get("texto")},
                    banco_de_questoes_id=q.id,
                    modelo_id=modelo_id,
                    input_tokens=random.randint(50, 200),
                    output_tokens=random.randint(20, 100),
                    total_tokens=random.randint(70, 300)
                )
                session.add(res_mock)
                await session.flush()

                # Definir range de indicador baseado no tipo de métrica
                # A maioria das métricas usa 0-3 ou 0-6 no avaliador real,
                # Compreensão Textual e Clareza usam 0 ou 100 no engine.
                if tipo_metrica in [TipoMetrica.CompreensaoTextual, TipoMetrica.ClarezaResposta]:
                    valor_indicador = random.choice([0, 100])
                elif tipo_metrica == TipoMetrica.TesteDoEmbed:
                    valor_indicador = random.randint(0, 6)
                else:
                    valor_indicador = random.randint(0, 3)

                ind_mock = Indicadores(
                    indicador=valor_indicador,
                    modelo_id=modelo_id,
                    metrica_id=metrica_id
                )
                session.add(ind_mock)

        await session.commit()
        print("Mock data seeded for all metrics.")

if __name__ == "__main__":
    asyncio.run(seed_data())
