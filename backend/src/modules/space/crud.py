from fastcrud import FastCRUD

from .models import Space, SpaceUser

crud_spaces: FastCRUD = FastCRUD(Space)
crud_space_users: FastCRUD = FastCRUD(SpaceUser)
