from typing import List
from pydantic import BaseModel, Field


class Product(BaseModel):
    name: str = Field(...)
    description: List[str] = Field([])
    ratingStar: str = Field(...)
    ratingCount: str = Field(...)
    price: float = Field(...)
    exchange: str = Field(...)
    image: List[str] = Field([])
    link: str = Field(...)


class ProductList(BaseModel):
    status: int = Field(...)
    products: List[Product] = Field(...)
    served_through_cache: bool = Field(...)


class ProductResults(BaseModel):
    results: ProductList = Field(...)