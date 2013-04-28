# -*- coding: utf-8 -*-
from flask import url_for, redirect, request
from flask.ext.databrowser.action import DeleteAction, BaseAction, ReadOnlyAction
from lite_mms.constants import cargo as cargo_const


class MyDeleteAction(DeleteAction):

    def test_enabled(self, model):
        if model.goods_receipt_list:
            return -2
        return 0

    def get_forbidden_msg_formats(self):
        return {-2: u"收货会话%s已经生成了收货单，请先删除对应收货单以后再删除此收货会话!"}


class CloseAction(BaseAction):

    def test_enabled(self, model):
        if model.status in [cargo_const.STATUS_CLOSED, cargo_const.STATUS_DISMISSED]:
            return -2
        if not all(task.weight for task in model.task_list):
            return -3
        return 0

    def op(self, obj):
        from lite_mms.portal.cargo.fsm import fsm
        from flask.ext.login import current_user
        fsm.reset_obj(obj)
        fsm.next(cargo_const.ACT_CLOSE, current_user)

    def get_forbidden_msg_formats(self):
        return {-2: u"收货会话%s已经被关闭", 
                -3: u"收货会话%s有卸货任务没有称重，请确保所有的卸货任务都已经称重！"}


class OpenAction(ReadOnlyAction):

    def test_enabled(self, model):
        if model.status != cargo_const.STATUS_CLOSED:
            return -2
        return 0

    def op(self, obj):
        from lite_mms.portal.cargo.fsm import fsm
        from flask.ext.login import current_user
        fsm.reset_obj(obj)
        fsm.next(cargo_const.ACT_OPEN, current_user)

    def get_forbidden_msg_formats(self):
        return {-2: u"收货会话%s处在打开状态, 只有已经关闭的会话才能被打开"}

class CreateReceiptAction(ReadOnlyAction):

    def test_enabled(self, model):
        if model.goods_receipt_list and all(
                not gr.stale for gr in model.goods_receipt_list):
            return -2
        return 0

    def op(self, obj):
        obj.clean_goods_receipts()

    def get_forbidden_msg_formats(self):
        return {-2: u"%s已生成收货单"}


class PrintGoodsReceipt(BaseAction):

    def op_upon_list(self, objs, model_view):
        model_view.do_update_log(objs[0], self.name)
        return redirect(url_for("cargo.goods_receipt_preview", id_=objs[0].id, url=request.url))