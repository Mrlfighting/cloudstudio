"""常规 CRUD 沿用骨架；版本比较写入由服务层原子 SQL 完成。"""

from fastcrud import FastCRUD

from .models import BeadPattern

crud_bead_patterns: FastCRUD = FastCRUD(BeadPattern)
