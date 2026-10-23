"""Palermo-2: independent, fail-closed G5 financial and evidence reconciliation."""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from mcias.audit_agents import AGENTS

def _finite(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return number if number.is_finite() and number >= 0 else None

def verify(claim, findings, calculation, *, policy_fingerprint=None, policy_id=None, reference_check=None):
    issues = []
    if (not isinstance(findings, list) or len(findings) != len(AGENTS)
        or {x.get("agent") for x in findings if isinstance(x, dict)} != set(AGENTS)):
        issues.append("missing_or_duplicate_agent")
    if (not isinstance(findings, list)
        or any(not isinstance(x, dict) or x.get("status") != "pass" for x in findings)):
        issues.append("unresolved_findings")
    if not isinstance(calculation, dict) or calculation.get("status") != "calculated":
        issues.append("calculation_held")
        calculation = calculation if isinstance(calculation, dict) else {}
    else:
        if reference_check is not None and calculation.get('amount_basis')!='NET':
            issues.append('NET_amount_basis_mismatch')
        original = _finite(claim.claimed_amount)
        claimed = _finite(calculation.get("claimed"))
        payable = _finite(calculation.get("payable"))
        steps = calculation.get("deductions")
        deductions = ([_finite(x.get("deduction")) if isinstance(x, dict) else None
                       for x in steps] if isinstance(steps, list) else [None])
        if (original is None or claimed is None or payable is None
            or any(x is None for x in deductions) or claimed != original):
            issues.append("invalid_monetary_values")
        else:
            if sum(deductions, Decimal(0)) + payable != claimed:
                issues.append("T09_financial_reconciliation_failed")
            disclosed_total = _finite(calculation.get("total_deduction"))
            if disclosed_total is None or disclosed_total != sum(deductions, Decimal(0)):
                issues.append("deduction_total_mismatch")
        if calculation.get('amount_basis')=='NET':
            issues.extend(_verify_net(claim,calculation))
            if policy_fingerprint is not None:
                if calculation.get('policy_fingerprint')!=policy_fingerprint:issues.append('NET_signed_policy_mismatch')
                if calculation.get('policy_id')!=policy_id:issues.append('NET_policy_id_mismatch')
                if not reference_check:issues.append('NET_reference_check_missing')
                else:
                    try:
                        refs={k:v for k,v in reference_check['references'].items() if k!='beneficiary_enrollment'}
                        ref_hash=sha256(json.dumps(refs,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
                        if calculation.get('reference_fingerprint')!=ref_hash:issues.append('NET_reference_binding_mismatch')
                        if calculation.get('source_columns')!=reference_check.get('source_columns'):issues.append('NET_confirmed_mapping_mismatch')
                        if calculation.get('invoice_evidence')!=reference_check.get('invoices'):issues.append('NET_invoice_binding_mismatch')
                        if calculation.get('contract_id')!=reference_check['references']['contract']['id']:issues.append('NET_contract_binding_mismatch')
                        if calculation.get('enrollment_id')!=reference_check['references']['beneficiary_enrollment']['id']:issues.append('NET_enrollment_binding_mismatch')
                    except (KeyError,TypeError,ValueError,AttributeError):issues.append('NET_invalid_reference_binding')
        if calculation.get("source_id") != claim.extracted_record_id:
            issues.append("source_mismatch")
        if calculation.get("currency") != claim.currency:
            issues.append("currency_mismatch")
        fingerprint = calculation.get("fingerprint")
        payload = {k: v for k, v in calculation.items() if k != "fingerprint"}
        try:
            expected = sha256(json.dumps(payload, sort_keys=True,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        except (ValueError, TypeError):
            expected = None
        if fingerprint != expected or expected is None:
            issues.append("calculation_fingerprint_mismatch")
    return {"status": "verified" if not issues else "held",
            "issues": issues, "claim_id": claim.id,
            "calculation_fingerprint": calculation.get("fingerprint")}

def _verify_net(claim,calculation):
    """Independent recomputation, without calling the producing audit engine."""
    from decimal import ROUND_HALF_UP, ROUND_HALF_EVEN
    issues=[]
    try:
        p=calculation['policy_definition'];g=calculation['gross_evidence']
        policy_hash=sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if p['amount_basis']!='NET' or policy_hash!=calculation['policy_fingerprint']:issues.append('NET_policy_mismatch')
        if p['reference_fingerprint']!=calculation['reference_fingerprint']:issues.append('NET_reference_mismatch')
        if sha256(json.dumps(claim.source_values,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=calculation['source_values_fingerprint']:
            issues.append('NET_original_source_mismatch')
        unit=Decimal(1).scaleb(-p['precision']);rounding={'HALF_UP':ROUND_HALF_UP,'HALF_EVEN':ROUND_HALF_EVEN}[p['rounding']]
        def quant(value):
            value=Decimal(str(value))
            if not value.is_finite() or value<0:raise ValueError('invalid NET proof')
            return value.quantize(unit,rounding=rounding)
        remaining=quant(g['claimed']);percent=Decimal(p['copay_percent']);qty=Decimal(calculation['quantity'])
        if not percent.is_finite() or not 0<=percent<=100 or not qty.is_finite() or qty<=0:raise ValueError('invalid NET policy')
        columns=calculation['source_columns'];raw=claim.source_values
        def original(key):return Decimal(str(raw[columns[key]]).strip().replace(',','').removesuffix('%'))
        source_qty=original('quantity') if 'quantity' in columns else Decimal(1)
        source_gross=original('gross_amount') if 'gross_amount' in columns else original('unit_price')*source_qty
        if source_qty!=qty or quant(source_gross)!=remaining:issues.append('NET_original_gross_mismatch')
        if quant(original('claimed_amount'))!=quant(claim.claimed_amount):issues.append('NET_original_net_mismatch')
        if 'copay_amount' in columns and quant(source_gross-original('copay_amount'))!=quant(claim.claimed_amount):
            issues.append('NET_source_arithmetic_mismatch')
        expected=[]
        for rule in ('exclusion','tariff','cap','copay'):
            if rule=='exclusion':deduction=quant(p['exclusion'])
            elif rule=='tariff':deduction=max(Decimal(0),remaining-quant(Decimal(p['tariff'])*qty))
            elif rule=='cap':
                if p['cap'] is None:continue
                deduction=max(Decimal(0),remaining-quant(p['cap']))
            else:deduction=quant(remaining*percent/100)
            deduction=min(remaining,quant(deduction));remaining=quant(remaining-deduction)
            expected.append({'rule':rule,'deduction':str(deduction),'remaining':str(remaining)})
        if expected!=g['deductions'] or remaining!=quant(g['payable']):issues.append('NET_gross_recomputation_failed')
        if quant(calculation['payable'])!=min(quant(claim.claimed_amount),remaining):issues.append('NET_payable_mismatch')
        if calculation.get('copay_deducted_again') is not False or any(s.get('rule')=='copay' for s in calculation['deductions']):issues.append('NET_double_copay')
        if not calculation.get('invoice_evidence'):issues.append('NET_missing_invoice')
    except (KeyError,TypeError,ValueError,ArithmeticError):issues.append('NET_invalid_evidence')
    return issues
