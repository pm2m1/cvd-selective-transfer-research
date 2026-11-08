"""Public conditional planning only. No count building, adoption or data APIs."""
from review_logic import classify_cell
import copy


def observability(participation, core, basis):
    interpretation, check = classify_cell(participation,core,basis)
    return {'frozen_target_check':check,'recorded_status_interpretation':interpretation,
            'eligibility_decisions_changed':False,'count_execution':'NO_EXECUTION'}


def defect_path():
    return {'status':'NOT_ESTABLISHED','patch_created':False,'count_execution':'NO_EXECUTION'}


def prospective_quarantine(history, *, disease_history=None):
    """UNADOPTED C-prototype over INVENTED status tuples, never disease values.

    A whole person is proposed for quarantine if ANY historical observation is
    not classified CONSISTENT by the existing diagnostic reference categories.
    All original observations remain in the returned history; no interval is
    deleted, no disease history is reset, no participant becomes eligible here.
    This intentionally conservative policy is NOT an adopted count algorithm.
    """
    flags = [classify_cell(*record)[0] != 'CONSISTENT' for record in history]
    return {'proposal':'UNADOPTED_WHOLE_PERSON_UNRESOLVED_STATUS_QUARANTINE',
            'proposed_quarantine':any(flags),'history':list(history),
            'unchanged_history_evidence':copy.deepcopy(disease_history),
            'eligible_for_count':None,'disease_outcome':None,'count_execution':'NO_EXECUTION'}
