import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)
class ExtraSalesTaxReports(models.TransientModel):
    _name="ar.extra.sales.tax.report"
    _description="Extra Sales Tax Reports"

    type_report = fields.Selection([('ivasale', 'Iva Venta por categorias')], string="Reporte", default='ivasale')
    date_from = fields.Date (string="Fecha Inicio")
    date_to = fields.Date (string="Fecha Fin")

    def print_report_xml(self):
        # redirect to /account/account_extra_sales_report to generate the excel file
        return {
            'type': 'ir.actions.act_url',
            'url': '/account/account_extra_sales_report/%s' % (self.id),
            'target': 'new',
        }

    def print_report(self):
        if self.type_report == 'ivasale':
            invoices_ids = self.env['account.move'].search([('state','=','posted'),('move_type','in',['out_invoice','out_refund']),('invoice_date','>=',self.date_from),('invoice_date','<=',self.date_to)])
            
            _categories = []
            _existing_categories = []
            for inv in invoices_ids:
                for il in inv.invoice_line_ids:

                    #Variables utilizadas para almacenar totales de impuestos por lineas
                    _impInt = 0
                    _impIVA = 0
                    _exento = 0
                    #Variable usada de bandera para saber si ya sumo el impuesto interno de una linea
                    _sumoInterno = 0
                    
                    #Primero se calcula cuanto de impuestos interno existe para luego poder calcular el iva ya que son impuestos incluidos en el precio
                    for tax in il.tax_ids:
                        #Se busca si la linea tiene impuestos internos y se guardan para luego sumar en su categoria
                        if tax.tax_group_id.l10n_ar_tribute_afip_code == '04' and _sumoInterno == 0:
                            _impInt += il.imp_int_total
                            _sumoInterno = 1
                    for tax in il.tax_ids:
                        #Se busca si la linea tiene IVA y se guarda para luego sumar a su categoria
                        if tax.tax_group_id.l10n_ar_vat_afip_code in ['4','5','6']:
                            #Calculo de iva si esta inluido en precio o no
                            if tax.price_include:
                                _impIVA += ((il.price_unit * il.quantity) - _impInt) - (((il.price_unit * il.quantity) - _impInt) / ((tax.amount /100) + 1))
                            else:
                                _impIVA += ((il.price_subtotal) - _impInt) * (tax.amount /100)
                        #Se busca si la linea tiene IVA Exento y se guarda para luego sumar a su categoria
                        elif tax.tax_group_id.l10n_ar_vat_afip_code == '2':
                            _exento += il.price_subtotal

                    

                    # Se obtiene categoria principal del producto
                    i = 0
                    _categ_tmp = self.env['product.category'].search([('id','=',il.product_id.categ_id.id)])
                    while i == 0 and _categ_tmp.name != False:
                        if not _categ_tmp.parent_id.name == False:
                            if _categ_tmp.parent_id.parent_id.name == False:
                                i = 1
                            else:
                                _categ_tmp = self.env['product.category'].search([('id','=',_categ_tmp.parent_id.id)])
                        else:
                            i = 1


                    # Si la categoria aun no se a detectado se agrega por primera vez y se cargan 
                    # los totales de la linea que contiene el producto de la nueva categoria
                    if not _categ_tmp.name in _existing_categories:
                        _vals={'categoria' : _categ_tmp.name,
                                'Neto' : il.price_subtotal,
                                'Imp. Int': _impInt,
                                'Iva': _impIVA,
                                'Exento' : _exento}
                        _categories.append(_vals)
                        _existing_categories.append(_categ_tmp.name)
                    # En el caso de que ya se haya cargado la categoria se suman los totales del producto de dicha categoria
                    else:
                        for cate in _categories:
                            if cate['categoria'] == _categ_tmp.name:
                                cate['Neto'] = cate['Neto'] + il.price_subtotal
                                cate['Imp. Int'] = cate['Imp. Int'] + _impInt
                                cate['Iva'] = cate['Iva'] + _impIVA
                                cate['Exento'] = cate['Exento'] + _exento
            data = {
                'from_data' : self.read()[0],
                'categories' : _categories
            }
            return self.env.ref('extra_sales_tax_report.action_report_iva_sale').sudo().with_context(landscape=True).report_action(self, data=data)
