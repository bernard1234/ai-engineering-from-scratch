# Task Frame：防止注册时出现重复邮箱地址

Status: READY

## Repository facts
- 账户写入使用 AccountStore（`app/accounts.py:18`）
- 重复错误使用 409 状态码（`tests/test_accounts.py:44`）

## Allowed paths
- `app/accounts.py`
- `tests/test_accounts.py`

## Forbidden paths
- `migrations/**`
- `deploy/**`

## Acceptance evidence
- `python3 -m unittest tests.test_accounts`

## Unknowns
- 邮箱比较是否区分大小写