"""add creator columnRevision ID: e8e10d94c8eRevises: 5a8040282a1fCreate Date: 2013-07-24 14:39:16.179000"""# revision identifiers, used by Alembic.revision = 'e8e10d94c8e'down_revision = '5a8040282a1f'from alembic import opimport sqlalchemy as sadef upgrade():    op.add_column("TB_GOODS_RECEIPT", sa.Column("creator_id", sa.Integer, sa.ForeignKey("TB_USER.id", "fk_creator_gr")))def downgrade():    op.drop_constraint("fk_creator_gr", "TB_GOODS_RECEIPT", type_="foreignkey")    op.drop_column("TB_GOODS_RECEIPT", "creator_id")