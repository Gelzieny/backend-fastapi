from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.models import TipoMetrica, Provider

class ProvedorBase(BaseModel):
    nome: Provider

class Provedor(ProvedorBase):
    id: int
    class Config:
        from_attributes = True

class ModeloBase(BaseModel):
    nome: str
    provedor_id: int

class Modelo(ModeloBase):
    id: int
    class Config:
        from_attributes = True

class MetricaBase(BaseModel):
    metricas: str
    tipo: TipoMetrica

class Metrica(MetricaBase):
    id: int
    class Config:
        from_attributes = True

class BancoDeQuestoesBase(BaseModel):
    metrica_id: int
    pergunta: dict
    gabarito: dict

class BancoDeQuestoes(BancoDeQuestoesBase):
    id: int
    class Config:
        from_attributes = True
