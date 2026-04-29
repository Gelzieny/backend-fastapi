import enum
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass

class Provider(enum.Enum):
    ollama = "ollama"

class TipoMetrica(enum.Enum):
    CompreensaoTextual = "CompreensaoTextual"
    ClarezaResposta = "ClarezaResposta"
    TesteDoEmbed = "TesteDoEmbed"
    DireitoAdministrativo = "DireitoAdministrativo"
    Matematica = "Matematica"
    RaciocinioLogico = "RaciocinioLogico"
    VibeCoding = "VibeCoding"

class CartaServico(Base):
    __tablename__ = "cartas_servico"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(String)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, name="metadata")
    # Embedding vector size should be adjusted based on the model used (e.g., 768, 1536)
    embedding = mapped_column(Vector(768), nullable=True) 

class Metricas(Base):
    __tablename__ = "metricas"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metricas: Mapped[str] = mapped_column(String)
    tipo: Mapped[TipoMetrica] = mapped_column(Enum(TipoMetrica))
    
    banco_de_questoes: Mapped[List["BancoDeQuestoes"]] = relationship(back_populates="metrica")
    indicadores: Mapped[List["Indicadores"]] = relationship(back_populates="metrica")

    __table_args__ = (UniqueConstraint("metricas", "tipo"),)

class BancoDeQuestoes(Base):
    __tablename__ = "banco_de_questoes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metrica_id: Mapped[int] = mapped_column(ForeignKey("metricas.id", ondelete="CASCADE"))
    
    pergunta: Mapped[dict] = mapped_column(JSON)
    gabarito: Mapped[dict] = mapped_column(JSON)
    
    metrica: Mapped["Metricas"] = relationship(back_populates="banco_de_questoes")
    resultados: Mapped[List["Resultados"]] = relationship(back_populates="banco_de_questoes")
    
    __table_args__ = (UniqueConstraint("id", "metrica_id"),)

class Provedores(Base):
    __tablename__ = "provedores"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[Provider] = mapped_column(Enum(Provider), unique=True)
    
    modelos: Mapped[List["Modelos"]] = relationship(back_populates="provedor")

class Modelos(Base):
    __tablename__ = "modelos"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String)
    provedor_id: Mapped[int] = mapped_column(ForeignKey("provedores.id", ondelete="CASCADE"))
    
    provedor: Mapped["Provedores"] = relationship(back_populates="modelos")
    resultados: Mapped[List["Resultados"]] = relationship(back_populates="modelo")
    indicadores: Mapped[List["Indicadores"]] = relationship(back_populates="modelo")
    
    __table_args__ = (UniqueConstraint("provedor_id", "nome"),)

class Resultados(Base):
    __tablename__ = "resultados"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    tipo_resultado: Mapped[TipoMetrica] = mapped_column(Enum(TipoMetrica))
    json_resultado: Mapped[Optional[dict]] = mapped_column(JSON)
    
    erro: Mapped[bool] = mapped_column(Boolean, default=False)
    json_erro: Mapped[Optional[dict]] = mapped_column(JSON)
    
    banco_de_questoes_id: Mapped[int] = mapped_column(ForeignKey("banco_de_questoes.id"))
    modelo_id: Mapped[int] = mapped_column(ForeignKey("modelos.id", ondelete="CASCADE"))
    
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    total_tokens: Mapped[int] = mapped_column(Integer)
    
    banco_de_questoes: Mapped["BancoDeQuestoes"] = relationship(back_populates="resultados")
    modelo: Mapped["Modelos"] = relationship(back_populates="resultados")
    
    __table_args__ = (UniqueConstraint("banco_de_questoes_id", "modelo_id"),)

class Indicadores(Base):
    __tablename__ = "indicadores"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    indicador: Mapped[int] = mapped_column(Integer)
    modelo_id: Mapped[int] = mapped_column(ForeignKey("modelos.id", ondelete="CASCADE"))
    metrica_id: Mapped[int] = mapped_column(ForeignKey("metricas.id"))
    
    modelo: Mapped["Modelos"] = relationship(back_populates="indicadores")
    metrica: Mapped["Metricas"] = relationship(back_populates="indicadores")
    
    __table_args__ = (UniqueConstraint("id", "modelo_id", "metrica_id"),)
