from pydantic import BaseModel
from pydantic.config import ConfigDict
from typing import List


class RoleBase(BaseModel):
  name: str
  is_admin: bool = False
  allowed_paths: List[str] = []


class RoleCreate(RoleBase):
  pass


class RoleUpdate(BaseModel):
  name: str | None = None
  is_admin: bool | None = None
  allowed_paths: List[str] | None = None


class RoleOut(RoleBase):
  id: int

  model_config = ConfigDict(from_attributes=True)


