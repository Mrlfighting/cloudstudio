from fastcrud import FastCRUD

from .models import Picture

crud_pictures: FastCRUD = FastCRUD(Picture)
