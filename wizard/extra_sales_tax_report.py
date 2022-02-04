import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)
class ExtraSalesTaxReports(models.TransientModel):
    _name="ar.extra.sales.tax.report"
    _description="Extra Sales Tax Reports"

    type_report = fields.Selection([('ivasale', 'Iva Venta por categorias')], string="Reporte", default='ivasale')
    date_from = fields.Date (string="Fecha Inicio")
    date_to = fields.Date (string="Fecha Fin")

    def print_report(self):
        if self.type_report == 'ivasale':
            invoices_ids = self.env['account.move'].search([('move_type','in',['out_invoice','out_refund']),('invoice_date','>=',self.date_from),('invoice_date','<=',self.date_to)])
            
            _categories = []
            _existing_categories = []
            for inv in invoices_ids:
                for il in inv.invoice_line_ids:
                    _logger.warning('******* lineas: {0}'.format(il.product_id.name))

                    #Variables utilizadas para almacenar totales de impuestos por lineas
                    _impInt = 0
                    _impIVA = 0
                    _exento = 0
                    
                    for tax in il.tax_ids:
                        #Se busca si la linea tiene IVA y se guarda para luego sumar a su categoria
                        if tax.tax_group_id.l10n_ar_vat_afip_code in ['4','5','6']:
                            #Calculo de iva si esta inluido en precio o no
                            if tax.price_include:
                                _impIVA += il.price_subtotal / ((tax.amount /100) + 1)
                            else:
                                _impIVA += il.price_subtotal * (tax.amount /100)
                            _logger.warning('******* Impuesto IVA: {0} en el producto: {1}'.format(tax.name, il.product_id.name))
                        #Se busca si la linea tiene impuestos internos y se guardan para luego sumar en su categoria
                        elif tax.tax_group_id.l10n_ar_tribute_afip_code == '04':
                            #Calculo de imp int si es porcentaje
                            if tax.amount_type == 'percent':
                                if tax.price_include:
                                    _impInt += il.price_subtotal / ((tax.amount /100) + 1)
                                else:
                                    _impInt += il.price_subtotal * (tax.amount /100)
                            #Calculo de imp int si es fijo
                            elif tax.amount_type == 'fixed':
                                _impInt += tax.amount
                            _logger.warning('******* Impuesto interno: {0} en el producto: {1}'.format(tax.name, il.product_id.name))
                        #Se busca si la linea tiene IVA Exento y se guarda para luego sumar a su categoria
                        elif tax.tax_group_id.l10n_ar_vat_afip_code == '2':
                            _exento += il.price_subtotal
                            _logger.warning('******* Exento: {0} en el producto: {1}'.format(tax.name, il.product_id.name))
                            
                    _logger.warning('******* Impuesto IVA: {0}'.format(_impIVA))
                    _logger.warning('******* Impuesto interno: {0}'.format(_impInt))
                    _logger.warning('******* Exento: {0}'.format(_exento))

                    

                    # Si la categoria aun no se a detectado se agrega por primera vez y se cargan 
                    # los totales de la linea que contiene el producto de la nueva categoria
                    if not il.product_id.categ_id.name in _existing_categories:
                        _vals={'categoria' : il.product_id.categ_id.name,
                                'Neto' : il.price_total,
                                'Imp. Int': _impInt,
                                'Iva': _impIVA,
                                'Exento' : _exento}
                        _categories.append(_vals)
                        _existing_categories.append(il.product_id.categ_id.name)
                    # En el caso de que ya se haya cargado la categoria se suman los totales del producto de dicha categoria
                    else:
                        for cate in _categories:
                            if cate['categoria'] == il.product_id.categ_id.name:
                                cate['Neto'] = cate['Neto'] + il.price_total
                                cate['Imp. Int'] = cate['Imp. Int'] + _impInt
                                cate['Iva'] = cate['Iva'] + _impIVA
                                cate['Exento'] = cate['Exento'] + _exento

                    
                    
                        
                    
            
            _logger.warning('******* _existing_categories: {0}'.format(_existing_categories))
            _logger.warning('******* _categories: {0}'.format(_categories))
            data = {
                'from_data' : self.read()[0],
                'categories' : _categories
            }
            return self.env.ref('extra_sales_tax_report.action_report_iva_sale').sudo().with_context(landscape=True).report_action(self, data=data)
