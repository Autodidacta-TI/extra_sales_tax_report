# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import content_disposition, request
from datetime import datetime
import io
import xlsxwriter
 
_logger = logging.getLogger(__name__)
class ExtraSalesTaxController(http.Controller):
    @http.route([
        '/account/account_extra_sales_report/<model("ar.extra.sales.tax.report"):wizard>',
    ], type='http', auth="user", csrf=False)
    def get_sale_excel_report(self,wizard=None,**args):
         
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Reporte de Facturas' + '.xlsx'))
                    ]
                )
 
        # Crea workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
 
        # Estilos de celdas
        title_style = workbook.add_format({'font_name': 'Times', 'font_size': 14, 'bold': True, 'align': 'center','bg_color': 'yellow', 'left': 1, 'bottom':1, 'right':1, 'top':1})
        header_style = workbook.add_format({'font_name': 'Times', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center'})
        text_style = workbook.add_format({'font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        number_style = workbook.add_format({'font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
        date_style = workbook.add_format({'num_format': 'dd/mm/yy','font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
        currency_style = workbook.add_format({'num_format':'$#,##0.00','font_name': 'Times', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
 
        # Crea worksheet
        sheet = workbook.add_worksheet("Reporte")
        # Orientacion landscape
        sheet.set_landscape()
        # Tamaño de papel A4
        sheet.set_paper(9)
        # Margenes
        sheet.set_margins(0.5,0.5,0.5,0.5)

        # Configuracion de ancho de columnas
        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)

        # Titulos de reporte
        sheet.merge_range('A1:E1', 'Reporte de impuestos por categorias', title_style)
         
        # Títulos de columnas
        sheet.write(1, 0, 'Categoria', header_style)
        sheet.write(1, 1, 'Neto', header_style)
        sheet.write(1, 2, 'Imp. Int.', header_style)
        sheet.write(1, 3, 'IVA', header_style)
        sheet.write(1, 4, 'Exento', header_style)

        row = 2
        number = 1

        #Busca todas las facturas
        #invoices = request.env['account.move'].search([('move_type','in',['out_invoice','out_refund']), ('invoice_date','>=', wizard.start_date), ('invoice_date','<=', wizard.end_date)])
        invoices_ids = request.env['account.move'].search([('state','=','posted'),('move_type','in',['out_invoice','out_refund']),('invoice_date','>=',wizard.date_from),('invoice_date','<=',wizard.date_to)])

        #Variables temporales  
        _categories = []
        _existing_categories = []
        _ivaTotal = 0
        _impIntTotal = 0
        _exentoTotal = 0
        _netoTotal = 0

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
                _categ_tmp = request.env['product.category'].search([('id','=',il.product_id.categ_id.id)])
                while i == 0 and _categ_tmp.name != False:
                    if not _categ_tmp.parent_id.name == False:
                        if _categ_tmp.parent_id.parent_id.name == False:
                            i = 1
                        else:
                            _categ_tmp = request.env['product.category'].search([('id','=',_categ_tmp.parent_id.id)])
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

        for category in _categories:
            # Documento de categorias
            sheet.write(row, 0, category['categoria'], text_style) 
            sheet.write(row, 1, category['Neto'], currency_style)
            sheet.write(row, 2, category['Imp. Int'], currency_style)
            sheet.write(row, 3, category['Iva'], currency_style)
            sheet.write(row, 4, category['Exento'], currency_style)

            _ivaTotal += category['Iva']
            _impIntTotal += category['Imp. Int']
            _exentoTotal += category['Exento']
            _netoTotal += category['Neto']

            row += 1
            number += 1

        # Imprimiendo totales
        sheet.write(row, 1, _netoTotal, currency_style)
        sheet.write(row, 2, _impIntTotal, currency_style)
        sheet.write(row, 3, _ivaTotal, currency_style)
        sheet.write(row, 4, _exentoTotal, currency_style)

        # Devuelve el archivo de Excel como respuesta, para que el navegador pueda descargarlo 
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
 
        return response


        #for invoice in invoices_ids:
 #
        #    #Busca todas las lineas de cada factura
        #    invoce_lines = request.env['account.move.line'].search([('move_id','=',invoice.id),('product_id','!=', False)])
#
        #    for line in invoce_lines:
        #        # Documento de venta
        #        sheet.write(row, 0, invoice.invoice_date, date_style) 
        #        sheet.write(row, 1, datetime.strptime(str(invoice.invoice_date), "%Y-%m-%d").strftime('%B'), text_style)
        #        sheet.write(row, 2, datetime.strptime(str(invoice.invoice_date), "%Y-%m-%d").strftime('%Y'), text_style)
        #        sheet.write(row, 3, invoice.l10n_latam_document_type_id.name, text_style)
        #        sheet.write(row, 4, invoice.name, text_style)
        #        sheet.write(row, 5, line.price_unit, currency_style)
        #        sheet.write(row, 6, line.quantity, number_style)
#
        #        # Definicion de producto
        #        #congelado / refrigerado / Seco
        #        if 'Refrigerados' in line.product_id.categ_id.display_name:
        #            sheet.write(row, 7, 'Refrigerados', number_style)
        #        elif 'Congelados' in line.product_id.categ_id.display_name:
        #            sheet.write(row, 7, 'Congelados', number_style)
        #        elif 'Secos' in line.product_id.categ_id.display_name:
        #            sheet.write(row, 7, 'Secos', number_style)
        #        else:
        #            sheet.write(row, 7, 'Otros', number_style)
        #        sheet.write(row, 8, line.product_id.type, number_style)
        #        sheet.write(row, 9, line.product_id.name, number_style)
        #        #Se buscan los datos necesarios para formarl el External ID de product.template
        #        model_data = request.env['ir.model.data'].search(([('model', '=', 'product.template'),('res_id','=',line.product_id.product_tmpl_id.id)]), limit=1)
        #        sheet.write(row, 10, "%s.%s" % (model_data.module, model_data.name), text_style)
        #        sheet.write(row, 11, line.product_id.uom_id.name, number_style)
        #        sheet.write(row, 12, invoice.name, text_style)# Reemplazar con proveedor / marca
#
        #        # Definicion del cliente
        #        sheet.write(row, 13, invoice.partner_id.name, text_style)
        #        model_data = request.env['ir.model.data'].search(([('model', '=', 'res.partner'),('res_id','=',invoice.partner_id.id)]), limit=1)
        #        sheet.write(row, 14, "%s.%s" % (model_data.module, model_data.name), text_style)
        #        sheet.write(row, 15, invoice.partner_id.comment, text_style)
        #        sheet.write(row, 16, invoice.partner_id.create_date, date_style)
        #        #sheet.write(row, 16, invoice.partner_id.internal_reference, text_style) #Nombre Fantasia
        #        sheet.write(row, 17, invoice.partner_id.name, text_style)
        #        sheet.write(row, 18, invoice.partner_id.street, text_style)
        #        sheet.write(row, 19, invoice.partner_id.zip, text_style)
        #        sheet.write(row, 20, invoice.partner_id.city, text_style)
        #        sheet.write(row, 21, invoice.partner_id.state_id.name, text_style)
        #        sheet.write(row, 22, invoice.partner_id.vat, text_style)
        #        sheet.write(row, 23, invoice.partner_id.l10n_ar_afip_responsibility_type_id.name, text_style)
        #        sheet.write(row, 24, invoice.partner_id.property_payment_term_id.name, text_style) #Forma de pago
        #        sheet.write(row, 25, invoice.partner_id.team_id.name, text_style)
        #        #sheet.write(row, 25, invoice.partner_id.delivery_day, text_style) #Dia Entrega
        #        sheet.write(row, 26, invoice.partner_id.name, text_style) #Dia Entrega
        #        #sheet.write(row, 26, invoice.partner_id.carrier_id.name, text_style) #Expreso
        #        sheet.write(row, 27, invoice.partner_id.name, text_style) #Expreso
        #        sheet.write(row, 28, invoice.partner_id.property_product_pricelist.name, text_style)
        #        sheet.write(row, 29, invoice.partner_id.mobile, text_style)
        #        sheet.write(row, 30, invoice.partner_id.phone, text_style)
        #        sheet.write(row, 31, invoice.partner_id.email, text_style)
        #        #sheet.write(row, 31, invoice.partner_id.net_captor, text_style) #Red Social
        #        sheet.write(row, 32, invoice.partner_id.name, text_style) #Red Social
        #        sheet.write(row, 33, invoice.partner_id.ref, text_style) #Red Social
 #
        #        row += 1
        #        number += 1
 #
        ## Devuelve el archivo de Excel como respuesta, para que el navegador pueda descargarlo 
        #workbook.close()
        #output.seek(0)
        #response.stream.write(output.read())
        #output.close()
 #
        #return response