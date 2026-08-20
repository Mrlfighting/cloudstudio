from fastcrud import FastCRUD

from .models import Space

crud_spaces: FastCRUD = FastCRUD(Space)
