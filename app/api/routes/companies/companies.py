from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.companies.company import CompanyCreate, CompanyOut, CompanyUpdate, YCloudConfig, YCloudTestResult
from app.services.companies import (
  list_companies,
  create_company,
  get_company,
  update_company,
  delete_company,
  update_ycloud_config,
)
from app.services.ycloud import create_ycloud_service


router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyOut])
@router.get("/", response_model=list[CompanyOut])
def list_(db: Session = Depends(get_db)):
  return list_companies(db)


@router.post("", response_model=CompanyOut)
@router.post("/", response_model=CompanyOut)
def create(payload: CompanyCreate, db: Session = Depends(get_db)):
  return create_company(db, payload)


@router.get("/{company_id}", response_model=CompanyOut)
def get(company_id: int, db: Session = Depends(get_db)):
  company = get_company(db, company_id)
  if not company:
    raise HTTPException(status_code=404, detail="Empresa no encontrada")
  return company


@router.put("/{company_id}", response_model=CompanyOut)
def update(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
  company = update_company(db, company_id, payload)
  if not company:
    raise HTTPException(status_code=404, detail="Empresa no encontrada")
  return company


@router.delete("/{company_id}")
def delete(company_id: int, db: Session = Depends(get_db)):
  ok = delete_company(db, company_id)
  if not ok:
    raise HTTPException(status_code=404, detail="Empresa no encontrada")
  return {"ok": True}


@router.put("/{company_id}/ycloud-config", response_model=CompanyOut)
def update_ycloud_configuration(
  company_id: int, 
  config: YCloudConfig, 
  db: Session = Depends(get_db)
):
  """Actualizar configuración de YCloud para la empresa"""
  company = update_ycloud_config(db, company_id, config)
  if not company:
    raise HTTPException(status_code=404, detail="Empresa no encontrada")
  return company


@router.post("/{company_id}/test-ycloud", response_model=YCloudTestResult)
async def test_ycloud_connection(company_id: int, db: Session = Depends(get_db)):
  """Probar la conexión con YCloud"""
  company = get_company(db, company_id)
  if not company:
    raise HTTPException(status_code=404, detail="Empresa no encontrada")
  
  if not company.ycloud_api_key:
    raise HTTPException(
      status_code=400, 
      detail="No hay API Key de YCloud configurada para esta empresa"
    )
  
  try:
    ycloud_service = create_ycloud_service(company.ycloud_api_key)
    result = await ycloud_service.test_connection()
    
    # Si la conexión es exitosa y obtenemos un número de teléfono, actualizarlo
    if result.success and result.phone_number and not company.whatsapp_phone_number:
      from app.schemas.companies.company import YCloudConfig
      update_config = YCloudConfig(
        api_key=company.ycloud_api_key,
        phone_number=result.phone_number,
        webhook_url=company.ycloud_webhook_url
      )
      update_ycloud_config(db, company_id, update_config)
    
    return result
  except Exception as e:
    return YCloudTestResult(
      success=False,
      message=f"Error al probar la conexión: {str(e)}"
    )


