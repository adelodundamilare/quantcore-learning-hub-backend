import pytest
from tests.helpers.asserts import api_call

ROLES=["super_admin","school_admin","teacher","student"]
CASES=[
    ("GET","/reports/admin/dashboard/stats",{"super_admin":200,"school_admin":403,"teacher":403,"student":403}),
    ("GET","/schools/admin/schools",{"super_admin":200,"school_admin":403,"teacher":403,"student":403}),
    ("GET","/courses/",{"super_admin":200,"school_admin":200,"teacher":200,"student":200}),
    ("GET","/trading/portfolio",{"super_admin":200,"school_admin":200,"teacher":200,"student":200}),
    ("GET","/trading/watchlists",{"super_admin":200,"school_admin":200,"teacher":200,"student":200}),
    ("GET","/trading/trade/history",{"super_admin":200,"school_admin":200,"teacher":200,"student":200}),
    ("GET","/billing/subscriptions",{"super_admin":200,"school_admin":200,"teacher":403,"student":403}),
    ("GET","/exams/",{"super_admin":200,"school_admin":200,"teacher":200,"student":200}),
]

@pytest.mark.parametrize("method,path,expect",CASES,ids=[f"{m} {p}" for m,p,_ in CASES])
@pytest.mark.parametrize("role",ROLES)
def test_rbac_matrix(client, token_for_role, method, path, expect, role):
    headers={"Authorization":f"Bearer {token_for_role(role)}"}
    response=client.request(method,path,headers=headers)
    status=response.status_code
    allowed=expect[role]==200
    if allowed:
        assert (200<=status<300) or status==404, f"{role} {method} {path} => {status}, body={response.text}"
    else:
        assert status==403 or status==404, f"{role} {method} {path} => {status}, body={response.text}"