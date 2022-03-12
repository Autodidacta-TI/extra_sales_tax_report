import logging

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move.line"
    
    imp_int_total = fields.Float('Total impuesto interno')

    def write(self, vals):
        
        
        res = super(AccountMove, self).write(vals)
        _logger.warning('******* Entro')
        for rec in self:
            if 'imp_int_total' not in vals:
                rec.imp_int_total = 0
                for imp in rec.tax_ids:
                    if imp.tax_group_id.l10n_ar_tribute_afip_code == '04':
                        #Calculo de imp int si es porcentaje
                        if imp.amount_type == 'percent':
                            if imp.price_include:
                                rec.imp_int_total += ((rec.price_unit * rec.quantity) - rec.imp_int_total) - (((rec.price_unit * rec.quantity) - rec.imp_int_total) / ((imp.amount /100) + 1))
                            else:
                                rec.imp_int_total += rec.price_subtotal * (imp.amount /100)
                        #Calculo de imp int si es fijo
                        elif imp.amount_type == 'fixed':
                            rec.imp_int_total += imp.amount
        return res
