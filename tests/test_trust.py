import pytest
from py_ai_memory.store import create_event, append_event
from py_ai_memory.trust import compute_trust_state, correct_event, reject_event, verify_event, get_supersession_chain, get_rejected_ids

def test_compute_trust_state(memory_dir):
    evt_verified = create_event('observe', 'test', source='observed')
    evt_candidate = create_event('observe', 'test', source='inferred')
    evt_rejected = create_event('reject', 'test')
    
    events = [evt_verified, evt_candidate, evt_rejected]
    
    assert compute_trust_state(evt_verified, events) == 'verified'
    assert compute_trust_state(evt_candidate, events) == 'candidate'
    assert compute_trust_state(evt_rejected, events) == 'rejected'
    
    evt_superseded = create_event('observe', 'old')
    evt_corrector = create_event('correct', 'new', supersedes=evt_superseded['id'])
    events.extend([evt_superseded, evt_corrector])
    
    assert compute_trust_state(evt_superseded, events) == 'superseded'

def test_trust_actions(memory_dir):
    target = create_event('observe', 'target', source='inferred')
    t_id = append_event(memory_dir, target)
    
    # correct
    corrected = correct_event(memory_dir, t_id, 'new val')
    assert corrected['supersedes'] == t_id
    
    # reject
    rejected = reject_event(memory_dir, t_id, 'wrong')
    assert rejected['type'] == 'reject'
    assert rejected['supersedes'] == t_id
    assert rejected['reason'] == 'wrong'
    
    with pytest.raises(ValueError):
        reject_event(memory_dir, t_id, 'already rejected')
        
    # verify
    target2 = create_event('observe', 'target2', source='inferred')
    t2_id = append_event(memory_dir, target2)
    verified = verify_event(memory_dir, t2_id)
    assert verified['source'] == 'observed'

def test_chain_and_rejected_ids(memory_dir):
    evt1 = create_event('observe', '1')
    id1 = append_event(memory_dir, evt1)
    evt2 = correct_event(memory_dir, id1, '2')
    evt3 = correct_event(memory_dir, evt2['id'], '3')
    
    chain = get_supersession_chain(memory_dir, evt3['id'])
    assert len(chain) == 3
    assert chain[0]['id'] == id1
    assert chain[2]['id'] == evt3['id']
    
    rej = reject_event(memory_dir, evt3['id'], 'bad')
    rej_ids = get_rejected_ids(memory_dir)
    assert evt3['id'] in rej_ids
    assert rej['id'] in rej_ids
