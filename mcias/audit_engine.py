"""G5 deterministic financial calculation. No AI financial decisions.

All ranges are Decimal, and each monetary stage operates on the remaining
eligible amount. Policy is explicit and versioned; absence blocks processing.
"""
from dataclasses import dataclass, replace, asdict
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
from hashlib import sha256
import json

D=Decimal
class PolicyBlocked(ValueError): pass

@dataclass(frozen=True)
class AuditPolicy:
    policy_id: str
    currency: str
    rounding: str
    precision: int
    order: tuple[str,...]
    copay_percent: Decimal
    cap: Decimal | None
    exclusion: Decimal
    tariff: Decimal
    approved: bool=False
    amount_basis: str='GROSS'
    reference_fingerprint: str|None=None

    def validate(self):
        import re
        if self.amount_basis not in ('GROSS','NET'):raise PolicyBlocked('unknown amount basis')
        if self.amount_basis=='NET' and not re.fullmatch('[0-9a-f]{64}',self.reference_fingerprint or ''):
            raise PolicyBlocked('NET policy must bind exact reference versions')
        if not self.approved or not self.policy_id:
            raise PolicyBlocked("written approved financial policy required")
        if self.rounding not in ("HALF_UP","HALF_EVEN") or self.precision not in (0,2,4):
            raise PolicyBlocked("unapproved rounding")
        if self.order != ("exclusion","tariff","cap","copay"):
            raise PolicyBlocked("deduction order requires explicit approval of exclusion, tariff, cap, copay")
        if len(self.currency)!=3 or not self.currency.isupper():
            raise PolicyBlocked("invalid currency")
        if not self.copay_percent.is_finite() or not D(0)<=self.copay_percent<=D(100):
            raise PolicyBlocked("invalid copay")
        if any(not x.is_finite() or x<0 for x in (self.tariff,self.exclusion)):
            raise PolicyBlocked("invalid tariff or exclusion")
        if self.cap is not None and (not self.cap.is_finite() or self.cap<0):
            raise PolicyBlocked("invalid cap")

def money(value,policy):
    value=D(str(value))
    if not value.is_finite() or value<0:
        raise PolicyBlocked("invalid monetary value")
    unit=D(1).scaleb(-policy.precision)
    return value.quantize(unit,rounding={"HALF_UP":ROUND_HALF_UP,"HALF_EVEN":ROUND_HALF_EVEN}[policy.rounding])

def evaluate(claimed: Decimal, currency: str, policy: AuditPolicy, *,
             eligible: bool, evidence_complete: bool, source_id: str,
             contract_id: str, beneficiary_enrollment_id: str) -> dict:
    policy.validate()
    if policy.amount_basis!='GROSS':raise PolicyBlocked('NET policy requires the NET evaluation path')
    if currency!=policy.currency:
        raise PolicyBlocked("currency conversion not authorized")
    if not all((source_id,contract_id,beneficiary_enrollment_id)):
        raise PolicyBlocked("reference provenance incomplete")
    claimed=money(claimed,policy)
    if not eligible or not evidence_complete:
        return {"status":"held","reason":"eligibility" if not eligible else "missing_evidence",
                "claimed":str(claimed),"deductions":[],"payable":None,
                "policy_id":policy.policy_id,"source_id":source_id}
    remaining=claimed
    steps=[]
    def deduct(kind,amount):
        nonlocal remaining
        amount=min(remaining,money(amount,policy))
        remaining=money(remaining-amount,policy)
        steps.append({"rule":kind,"deduction":str(amount),"remaining":str(remaining)})
    deduct("exclusion",policy.exclusion)
    deduct("tariff",max(D(0),remaining-policy.tariff))
    if policy.cap is not None:
        deduct("cap",max(D(0),remaining-policy.cap))
    deduct("copay",money(remaining*policy.copay_percent/D(100),policy))
    total=sum((D(s["deduction"]) for s in steps),D(0))
    if money(total+remaining,policy)!=claimed:
        raise ArithmeticError("T08 double deduction or reconciliation mismatch")
    result={"status":"calculated","claimed":str(claimed),"deductions":steps,
            "total_deduction":str(money(total,policy)),"payable":str(remaining),
            "currency":currency,"policy_id":policy.policy_id,"source_id":source_id,
            "contract_id":contract_id,"enrollment_id":beneficiary_enrollment_id}
    result["fingerprint"]=sha256(json.dumps(result,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return result

def policy_definition(policy):
    policy.validate()
    data={key:(str(value) if isinstance(value,Decimal) else list(value) if isinstance(value,tuple) else value)
          for key,value in asdict(policy).items()}
    # Preserve the exact signed fingerprints of historical GROSS policies.
    if policy.amount_basis=='GROSS' and policy.reference_fingerprint is None:
        data.pop('amount_basis');data.pop('reference_fingerprint')
    return data

def evaluate_net(claim,policy,reference_check):
    """Apply the existing gross rules once, reconcile against already-NET input."""
    policy.validate()
    if policy.amount_basis!='NET':raise PolicyBlocked('explicit NET policy required')
    context=reference_check['calculation']
    gross_policy=replace(policy,amount_basis='GROSS',reference_fingerprint=None,
                         tariff=policy.tariff*D(context['quantity']))
    gross=evaluate(D(context['gross']),claim.currency,gross_policy,eligible=True,evidence_complete=True,
        source_id=claim.extracted_record_id,contract_id=reference_check['references']['contract']['id'],
        beneficiary_enrollment_id=reference_check['references']['beneficiary_enrollment']['id'])
    claimed=money(claim.claimed_amount,policy);expected=D(gross['payable'])
    payable=min(claimed,expected);difference=claimed-payable
    definition=policy_definition(policy)
    result={'status':'calculated','amount_basis':'NET','claimed':str(claimed),'payable':str(payable),
        'total_deduction':str(difference),'deductions':[{'rule':'net_reference_adjustment','deduction':str(difference),'remaining':str(payable)}],
        'currency':claim.currency,'policy_id':policy.policy_id,'source_id':claim.extracted_record_id,
        'contract_id':reference_check['references']['contract']['id'],
        'enrollment_id':reference_check['references']['beneficiary_enrollment']['id'],
        'gross_evidence':gross,'policy_definition':definition,'quantity':context['quantity'],
        'policy_fingerprint':sha256(json.dumps(definition,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'source_values_fingerprint':sha256(json.dumps(claim.source_values,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'invoice_evidence':reference_check['invoices'],'reference_fingerprint':policy.reference_fingerprint,
        'source_columns':reference_check['source_columns'],
        'copay_deducted_again':False}
    result['fingerprint']=sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result
