from fastapi.testclient import TestClient
from app.main import app


def test_api_demo_provenance_and_cohort():
    with TestClient(app) as client:
        o = client.get('/api/options')
        assert o.status_code == 200
        assert o.json()['data_status'] == 'synthetic_demo'
        r = client.get('/api/case', params={'case_id': '20180112'})
        assert r.status_code == 200
        d = r.json()
        assert d['data_status'] == 'synthetic_demo'
        assert d['metrics']['n_members'] == 30
        assert len(d['step_w1']) == 5
        r = client.get('/api/cohort', params={'cohort': 'winter'})
        assert r.status_code == 200
        assert r.json()['summary']['n_cases'] == 4


def test_api_cache_miss_is_explicit():
    with TestClient(app) as client:
        r = client.get('/api/case', params={'case_id': '20180112', 'variable': 't2m'})
        assert r.status_code == 404
        assert 'not precomputed' in r.json()['detail']
        assert client.get('/api/case', params={'case_id': '../secret'}).status_code == 404
        assert client.get('/api/case', params={'case_id': '20180112', 'output_roi': 'none'}).status_code == 404
