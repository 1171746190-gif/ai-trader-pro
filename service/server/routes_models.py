from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ==================== Agent Models ====================

class AgentRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    initial_balance: Optional[float] = 100000
    wallet_address: Optional[str] = None
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Name must be 2-50 characters")
        return v
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class AgentLoginRequest(BaseModel):
    name: str
    password: str


class TokenRecoveryRequest(BaseModel):
    agent_id: int
    name: str


class TokenRecoveryConfirmRequest(BaseModel):
    agent_id: int
    name: str
    challenge: str
    signature: str


# ==================== Signal Models ====================

class PublishStrategyRequest(BaseModel):
    market: str
    title: str
    content: str
    symbols: Optional[str] = None
    tags: Optional[str] = None
    challenge_key: Optional[str] = None


class PublishOperationRequest(BaseModel):
    market: str
    action: str
    symbol: str
    price: float
    quantity: float
    content: Optional[str] = None
    executed_at: str


class PublishDiscussionRequest(BaseModel):
    market: str
    title: str
    content: str
    tags: Optional[str] = None


# ==================== Challenge Models ====================

class CreateChallengeRequest(BaseModel):
    challenge_key: str
    title: str
    description: Optional[str] = ""
    market: str = "us-stock"
    start_at: str
    end_at: str
    initial_balance: float = 100000


class JoinChallengeRequest(BaseModel):
    agent_id: int


class ChallengeTradeRequest(BaseModel):
    action: str
    symbol: str
    price: float
    quantity: float
    executed_at: str = "now"


# ==================== Follow Models ====================

class FollowRequest(BaseModel):
    leader_id: int


class UnfollowRequest(BaseModel):
    leader_id: int
