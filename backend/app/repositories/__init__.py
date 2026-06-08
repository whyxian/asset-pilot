"""数据访问层 — 封装所有数据源操作

数据库操作使用 SQLAlchemy AsyncSession，外部 API 调用使用对应 SDK。
services 层通过 repository 访问数据，不直接操作 session 或外部 API。
"""
