# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountCashboxLine(models.Model):
    _inherit = 'account.cashbox.line'

    default_pos_id = fields.Many2one('pos.config', string='This cashbox line is used by default when opening or closing a balance for this point of sale')

class AccountBankStmtCashWizard(models.Model):
    _inherit = 'account.bank.statement.cashbox'
    
    @api.model
    def default_get(self, fields):
        vals = super(AccountBankStmtCashWizard, self).default_get(fields)
        config_id = self.env.context.get('default_pos_id')
        if config_id:
            lines = self.env['account.cashbox.line'].search([('default_pos_id', '=', config_id)])
            if self.env.context.get('balance', False) == 'start':
                vals['cashbox_lines_ids'] = [[0, 0, {'coin_value': line.coin_value, 'number': line.number, 'subtotal': line.subtotal}] for line in lines]
            else:
                vals['cashbox_lines_ids'] = [[0, 0, {'coin_value': line.coin_value, 'number': 0, 'subtotal': 0.0}] for line in lines]
        return vals

class PosConfig(models.Model):
    _name = 'pos.config'

    def _default_sale_journal(self):
        journal = self.env.ref('point_of_sale.pos_sale_journal', raise_if_not_found=False)
        if journal and journal.sudo().company_id == self.env.user.company_id:
            return journal
        return self._default_invoice_journal()

    def _default_invoice_journal(self):
        return self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.user.company_id.id)], limit=1)

    def _default_pricelist(self):
        return self.env['product.pricelist'].search([], limit=1)

    def _get_default_location(self):
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)], limit=1).lot_stock_id

    def _get_default_nomenclature(self):
        return self.env['barcode.nomenclature'].search([], limit=1)

    def _get_group_pos_manager(self):
        return self.env.ref('point_of_sale.group_pos_manager')

    def _get_group_pos_user(self):
        return self.env.ref('point_of_sale.group_pos_user')

    def _compute_default_customer_html(self):
        return self.env['ir.qweb'].render('point_of_sale.customer_facing_display_html')

    name = fields.Char(string='Point of Sale Name', index=True, required=True, help="An internal identification of the point of sale")
    journal_ids = fields.Many2many(
        'account.journal', 'pos_config_journal_rel',
        'pos_config_id', 'journal_id', string='Available Payment Methods',
        domain="[('journal_user', '=', True ), ('type', 'in', ['bank', 'cash'])]",)
    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type')
    use_existing_lots = fields.Boolean(related='picking_type_id.use_existing_lots')
    stock_location_id = fields.Many2one(
        'stock.location', string='Stock Location',
        domain=[('usage', '=', 'internal')], required=True, default=_get_default_location)
    journal_id = fields.Many2one(
        'account.journal', string='Sales Journal',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to post sales entries.",
        default=_default_sale_journal)
    invoice_journal_id = fields.Many2one(
        'account.journal', string='Invoice Journal',
        domain=[('type', '=', 'sale')],
        help="Accounting journal used to create invoices.",
        default=_default_invoice_journal)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', string="Currency")
    iface_cashdrawer = fields.Boolean(string='Cashdrawer', help="Automatically open the cashdrawer")
    iface_payment_terminal = fields.Boolean(string='Payment Terminal', help="Enables Payment Terminal integration")
    iface_electronic_scale = fields.Boolean(string='Electronic Scale', help="Enables Electronic Scale integration")
    iface_vkeyboard = fields.Boolean(string='Virtual KeyBoard', help="Enables an integrated Virtual Keyboard")
    iface_customer_facing_display = fields.Boolean(string='Customer Facing Display', help="Enables a remotely connected customer facing display")
    iface_print_via_proxy = fields.Boolean(string='Print via Proxy', help="Bypass browser printing and prints via the hardware proxy")
    iface_scan_via_proxy = fields.Boolean(string='Scan via Proxy', help="Enable barcode scanning with a remotely connected barcode scanner")
    iface_invoicing = fields.Boolean(string='Invoicing', help='Enables invoice generation from the Point of Sale', default=True)
    iface_big_scrollbars = fields.Boolean('Large Scrollbars', help='For imprecise industrial touchscreens')
    iface_print_auto = fields.Boolean(string='Automatic Receipt Printing', default=False,
        help='The receipt will automatically be printed at the end of each order')
    iface_print_skip_screen = fields.Boolean(string='Skip Receipt Screen', default=True,
        help='The receipt screen will be skipped if the receipt can be printed automatically.')
    iface_precompute_cash = fields.Boolean(string='Prefill Cash Payment',
        help='The payment input will behave similarily to bank payment input, and will be prefilled with the exact due amount')
    iface_tax_included = fields.Boolean(string='Include Taxes in Prices',
        help='The displayed prices will always include all taxes, even if the taxes have been setup differently')
    iface_start_categ_id = fields.Many2one('pos.category', string='Start Category',
        help='The point of sale will display this product category by default. If no category is specified, all available products will be shown')
    iface_display_categ_images = fields.Boolean(string='Display Category Pictures',
        help="The product categories will be displayed with pictures.")
    restrict_price_control = fields.Boolean(string='Restrict Price Modifications to Managers',
        help="Check to box to restrict the price control to managers only on point of sale orders.")
    cash_control = fields.Boolean(string='Cash Control', help="Check the amount of the cashbox at opening and closing.")
    receipt_header = fields.Text(string='Receipt Header', help="A short text that will be inserted as a header in the printed receipt")
    receipt_footer = fields.Text(string='Receipt Footer', help="A short text that will be inserted as a footer in the printed receipt")
    proxy_ip = fields.Char(string='IP Address', size=45,
        help='The hostname or ip address of the hardware proxy, Will be autodetected if left empty')
    active = fields.Boolean(default=True)
    uuid = fields.Char(readonly=True, default=lambda self: str(uuid.uuid4()),
        help='A globally unique identifier for this pos configuration, used to prevent conflicts in client-generated data')
    sequence_id = fields.Many2one('ir.sequence', string='Order IDs Sequence', readonly=True,
        help="This sequence is automatically created by Odoo but you can change it "
        "to customize the reference numbers of your orders.", copy=False)
    sequence_line_id = fields.Many2one('ir.sequence', string='Order Line IDs Sequence', readonly=True,
        help="This sequence is automatically created by Odoo but you can change it "
        "to customize the reference numbers of your orders lines.", copy=False)
    session_ids = fields.One2many('pos.session', 'config_id', string='Sessions')
    current_session_id = fields.Many2one('pos.session', compute='_compute_current_session', string="Current Session")
    current_session_state = fields.Char(compute='_compute_current_session')
    last_session_closing_cash = fields.Float(compute='_compute_last_session')
    last_session_closing_date = fields.Date(compute='_compute_last_session')
    pos_session_username = fields.Char(compute='_compute_current_session_user')
    group_by = fields.Boolean(string='Group Journal Items', default=True,
        help="Check this if you want to group the Journal Items by Product while closing a Session")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, default=_default_pricelist)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    barcode_nomenclature_id = fields.Many2one('barcode.nomenclature', string='Barcodes', required=True, default=_get_default_nomenclature,
        help='Defines what kind of barcodes are available and how they are assigned to products, customers and cashiers')
    group_pos_manager_id = fields.Many2one('res.groups', string='Point of Sale Manager Group', default=_get_group_pos_manager,
        help='This field is there to pass the id of the pos manager group to the point of sale client')
    group_pos_user_id = fields.Many2one('res.groups', string='Point of Sale User Group', default=_get_group_pos_user,
        help='This field is there to pass the id of the pos user group to the point of sale client')
    tip_product_id = fields.Many2one('product.product', string='Tip Product',
        help="The product used to encode the customer tip. Leave empty if you do not accept tips.")
    fiscal_position_ids = fields.Many2many('account.fiscal.position', string='Fiscal Positions')
    default_fiscal_position_id = fields.Many2one('account.fiscal.position', string='Default Fiscal Position')
    default_cashbox_lines_ids = fields.One2many('account.cashbox.line', 'default_pos_id', string='Default Balance')
    customer_facing_display_html = fields.Html(string='Customer facing display content', translate=True, default=_compute_default_customer_html)

    @api.depends('journal_id.currency_id', 'journal_id.company_id.currency_id')
    def _compute_currency(self):
        for pos_config in self:
            if pos_config.journal_id:
                pos_config.currency_id = pos_config.journal_id.currency_id.id or pos_config.journal_id.company_id.currency_id.id
            else:
                pos_config.currency_id = self.env.user.company_id.currency_id.id

    @api.depends('session_ids')
    def _compute_current_session(self):
        for pos_config in self:
            session = pos_config.session_ids.filtered(lambda r: r.user_id.id == self.env.uid and \
                not r.state == 'closed' and \
                not r.rescue)
            # sessions ordered by id desc
            pos_config.current_session_id = session and session[0].id or False
            pos_config.current_session_state = session and session[0].state or False

    @api.depends('session_ids')
    def _compute_last_session(self):
        PosSession = self.env['pos.session']
        for pos_config in self:
            session = PosSession.search_read(
                [('config_id', '=', pos_config.id), ('state', '=', 'closed')],
                ['cash_register_balance_end_real', 'stop_at'],
                order="stop_at desc", limit=1)
            if session:
                pos_config.last_session_closing_cash = session[0]['cash_register_balance_end_real']
                pos_config.last_session_closing_date = session[0]['stop_at']
            else:
                pos_config.last_session_closing_cash = 0
                pos_config.last_session_closing_date = False

    @api.depends('session_ids')
    def _compute_current_session_user(self):
        for pos_config in self:
            session = pos_config.session_ids.filtered(lambda s: s.state == 'opened' and not s.rescue)
            pos_config.pos_session_username = session and session[0].user_id.name or False

    @api.constrains('company_id', 'stock_location_id')
    def _check_company_location(self):
        if self.stock_location_id.company_id and self.stock_location_id.company_id.id != self.company_id.id:
            raise UserError(_("The company of the stock location is different than the one of point of sale"))

    @api.constrains('company_id', 'journal_id')
    def _check_company_journal(self):
        if self.journal_id and self.journal_id.company_id.id != self.company_id.id:
            raise UserError(_("The company of the sales journal is different than the one of point of sale"))

    @api.constrains('company_id', 'invoice_journal_id')
    def _check_company_journal(self):
        if self.invoice_journal_id and self.invoice_journal_id.company_id.id != self.company_id.id:
            raise UserError(_("The invoice journal and the point of sale must belong to the same company"))

    @api.constrains('company_id', 'journal_ids')
    def _check_company_payment(self):
        if self.env['account.journal'].search_count([('id', 'in', self.journal_ids.ids), ('company_id', '!=', self.company_id.id)]):
            raise UserError(_("The company of a payment method is different than the one of point of sale"))

    @api.constrains('fiscal_position_ids', 'default_fiscal_position_id')
    def _check_default_fiscal_position(self):
        if self.default_fiscal_position_id and self.default_fiscal_position_id not in self.fiscal_position_ids:
            raise UserError(_("The default fiscal position must be included in the available fiscal positions of the point of sale"))

    @api.onchange('iface_print_via_proxy')
    def _onchange_iface_print_via_proxy(self):
        self.iface_print_auto = self.iface_print_via_proxy

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        if self.picking_type_id.default_location_src_id.usage == 'internal' and self.picking_type_id.default_location_dest_id.usage == 'customer':
            self.stock_location_id = self.picking_type_id.default_location_src_id.id

    @api.multi
    def name_get(self):
        result = []
        for config in self:
            if (not config.session_ids) or (config.session_ids[0].state == 'closed'):
                result.append((config.id, config.name + ' (' + _('not used') + ')'))
                continue
            result.append((config.id, config.name + ' (' + config.session_ids[0].user_id.name + ')'))
        return result

    @api.model
    def create(self, values):
        IrSequence = self.env['ir.sequence'].sudo()
        val = {
            'name': _('POS Order %s') % values['name'],
            'padding': 4,
            'prefix': "%s/" % values['name'],
            'code': "pos.order",
            'company_id': values.get('company_id', False),
        }
        # force sequence_id field to new pos.order sequence
        values['sequence_id'] = IrSequence.create(val).id

        val.update(name=_('POS order line %s') % values['name'], code='pos.order.line')
        values['sequence_line_id'] = IrSequence.create(val).id
        return super(PosConfig, self).create(values)

    @api.multi
    def unlink(self):
        for pos_config in self.filtered(lambda pos_config: pos_config.sequence_id or pos_config.sequence_line_id):
            pos_config.sequence_id.unlink()
            pos_config.sequence_line_id.unlink()
        return super(PosConfig, self).unlink()

    # Methods to open the POS
    @api.multi
    def open_ui(self):
        """ open the pos interface """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url':   '/pos/web/',
            'target': 'self',
        }

    @api.multi
    def open_session_cb(self):
        """ new session button

        create one if none exist
        access cash control interface if enabled or start a session
        """
        self.ensure_one()
        if not self.current_session_id:
            self.current_session_id = self.env['pos.session'].create({
                'user_id': self.env.uid,
                'config_id': self.id
            })
            if self.current_session_id.state == 'opened':
                return self.open_ui()
            return self._open_session(self.current_session_id.id)
        return self._open_session(self.current_session_id.id)

    @api.multi
    def open_existing_session_cb(self):
        """ close session button

        access session form to validate entries
        """
        self.ensure_one()
        return self._open_session(self.current_session_id.id)

    def _open_session(self, session_id):
        return {
            'name': _('Session'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'pos.session',
            'res_id': session_id,
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
