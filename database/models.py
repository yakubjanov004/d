from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict


@dataclass
class BaseModel:
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Users(BaseModel):
    id: Optional[int] = None
    telegram_id: Optional[int] = None
    full_name: Optional[str] = None
    username: Optional[str] = None
    phone: Optional[str] = None
    language: str = "uz"
    region: Optional[int] = None
    address: Optional[str] = None
    role: Dict[str, str] = field(
        default_factory=lambda: {
            "admin": "Administrator",
            "client": "Client",
            "manager": "Manager",
            "junior_manager": "Junior Manager",
            "controller": "Controller",
            "technician": "Technician",
            "warehouse": "Warehouse",
            "callcenter_supervisor": "Callcenter Supervisor",
            "callcenter_operator": "Callcenter Operator",
        }
    )
    abonent_id: Optional[str] = None
    is_blocked: bool = False


@dataclass
class Tarif(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    picture: Optional[str] = None

@dataclass
class ConnectionApplication(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    region: Optional[str] = None
    address: Optional[str] = None
    tarif_id: Optional[int] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    rating: Optional[int] = None
    notes: Optional[str] = None
    jm_notes: Optional[str] = None
    is_active: bool = True
    status: Dict[str, str] = field(
        default_factory=lambda: {
            "in_manager": "Manager Assigned",
            "in_junior_manager": "Junior Manager Assigned",
            "in_controller": "Controller Assigned",
            "between_controller_technician": "Between Controller and Technician role",
            "in_technician": "Technician Assigned",
            "in_warehouse": "Warehouse Assigned",
            "in_technician_work": "Technician Working",
            "completed": "Completed",
        }
    )

@dataclass
class TechnicianApplication(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    region: Optional[int] = None
    abonent_id: Optional[str] = None
    address: Optional[str] = None
    media: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    description: Optional[str] = None
    description_ish: Optional[str] = None
    description_operator: Optional[str] = None
    status: Dict[str, str] = field(
        default_factory=lambda: {
            "in_controller": "Controller Assigned",
            "between_controller_technician": "Between Controller and Technician role",
            "in_technician": "Technician Assigned",
            "in_technician_work": "Technician Working",
            "in_warehouse": "Warehouse Assigned",
            "in_call_center_supervisor": "Call Center Supervisor Assigned",
            "in_call_center_operator": "Call Center Operator Assigned",
            "completed": "Completed",
        }
    )
    rating: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True

@dataclass
class SaffApplication(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    phone: Optional[str] = None
    region: Optional[int] = None
    abonent_id: Optional[str] = None
    tarif_id: Optional[int] = None
    address: Optional[str] = None
    description: Optional[str] = None
    status: Dict[str, str] = field(
        default_factory=lambda: {
            "in_call_center_supervisor": "Call Center Supervisor Assigned",
            "in_controller": "Controller Assigned",
            "in_technician": "Technician Assigned",
            "in_between_controller_technician": "Between Controller and Technician role",
            "in_technician_work": "Technician Working",
            "in_warehouse": "Warehouse Assigned",
            "in_call_center_operator": "Call Center Operator Assigned",
            "completed": "Completed",
        }
    )
    type_of_zayavka: Dict[str, str] = field(
        default_factory=lambda: {
            "connection": "Connection",
            "technician": "Technician",
        }
    )
    is_active: bool = True

@dataclass
class Connection(BaseModel):
    id: Optional[int] = None
    sender_id: Optional[int] = None
    sender_status: Optional[str] = None
    recipient_id: Optional[int] = None
    recipient_status: Optional[str] = None
    connecion_id: Optional[int] = None
    technician_id: Optional[int] = None
    saff_id: Optional[int] = None


@dataclass
class Materials(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    serial_number: Optional[str] = None


@dataclass
class MaterialRequests(BaseModel):
    id: Optional[int] = None
    description: Optional[str] = None
    user_id: Optional[int] = None
    applications_id: Optional[int] = None
    material_id: Optional[int] = None

@dataclass
class MaterialAndTechnican(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    material_id: Optional[int] = None
    quantity: Optional[int] = None