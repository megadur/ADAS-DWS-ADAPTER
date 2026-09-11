"""
ADAS-DWS XML Parser & KPI Aggregator
Parses ADAS-DWS v1.0 XML files (Ausbaustufe 1, 2, and 3).
Filters out PII (verkaeufer, verbraucher) for DSGVO compliance.
Calculates aggregate business metrics for Home Assistant sensors.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

# XML Namespaces used in ADAS-DWS
NAMESPACES = {
    'dws': 'http://www.adas.de/spec/dws/v1'
}

@dataclass
class ADASHeader:
    version: str = ""
    absender: str = ""
    erstellt_am: str = ""
    instanz_id: str = ""
    anbieter: str = ""
    systembezeichnung: str = ""

@dataclass
class ADASMetrics:
    header: ADASHeader = field(default_factory=ADASHeader)
    
    # Sales Metrics
    total_sales_count: int = 0
    total_sales_amount_cents: int = 0
    total_items_sold: int = 0
    
    # Stock / Inventory Metrics
    total_stock_items: int = 0
    total_stock_packs: int = 0
    expiring_90d_count: int = 0
    old_stock_180d_count: int = 0
    
    # Goods Receipt Metrics
    goods_receipts_count: int = 0
    goods_receipts_amount_cents: int = 0
    goods_receipts_packs: int = 0
    
    # Returns & Missed Sales
    returns_count: int = 0
    returns_amount_cents: int = 0
    missed_sales_count: int = 0
    missed_sales_requested_packs: int = 0


def _strip_tag_namespace(tag: str) -> str:
    """Helper to remove XML namespace prefix from tag string."""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag


def parse_adas_xml(xml_content_or_filepath: str) -> ADASMetrics:
    """
    Parses an ADAS-DWS XML string or file path and computes privacy-compliant KPIs.
    """
    metrics = ADASMetrics()
    
    try:
        if xml_content_or_filepath.strip().startswith('<'):
            root = ET.fromstring(xml_content_or_filepath)
        else:
            tree = ET.parse(xml_content_or_filepath)
            root = tree.getroot()
    except Exception as e:
        logger.error(f"Failed to parse ADAS XML: {e}")
        raise ValueError(f"Invalid ADAS-DWS XML data: {e}")

    # Parse Header
    kopf_elem = None
    for child in root:
        if _strip_tag_namespace(child.tag) == 'kopf':
            kopf_elem = child
            break
            
    if kopf_elem is not None:
        for item in kopf_elem:
            tag_name = _strip_tag_namespace(item.tag)
            val = (item.text or "").strip()
            if tag_name == 'version':
                metrics.header.version = val
            elif tag_name == 'absender':
                metrics.header.absender = val
            elif tag_name == 'erstelltAm':
                metrics.header.erstellt_am = val
            elif tag_name == 'instanzId':
                metrics.header.instanz_id = val
            elif tag_name == 'system':
                for sys_item in item:
                    sys_tag = _strip_tag_namespace(sys_item.tag)
                    if sys_tag == 'anbieter':
                        metrics.header.anbieter = (sys_item.text or "").strip()
                    elif sys_tag == 'systembezeichnung':
                        metrics.header.systembezeichnung = (sys_item.text or "").strip()

    # Parse Data Blocks
    for block in root:
        block_name = _strip_tag_namespace(block.tag)
        
        if block_name == 'verkaufsblock':
            _parse_verkaufsblock(block, metrics)
        elif block_name == 'lagerblock':
            _parse_lagerblock(block, metrics)
        elif block_name == 'wareneingangsblock':
            _parse_wareneingangsblock(block, metrics)
        elif block_name == 'retourenblock':
            _parse_retourenblock(block, metrics)
        elif block_name == 'neinverkaufsblock':
            _parse_neinverkaufsblock(block, metrics)
            
    return metrics


def _parse_verkaufsblock(verkaufsblock: ET.Element, metrics: ADASMetrics):
    """Processes verkaufsblock elements (totals, subtotals, subtotalzeilen)."""
    for elem in verkaufsblock:
        tag_name = _strip_tag_namespace(elem.tag)
        if tag_name == 'total':
            metrics.total_sales_count += 1
            for child in elem:
                c_tag = _strip_tag_namespace(child.tag)
                if c_tag == 'subtotal':
                    for sub_child in child:
                        sc_tag = _strip_tag_namespace(sub_child.tag)
                        if sc_tag == 'subtotalzeile':
                            metrics.total_items_sold += 1
                            for z_elem in sub_child:
                                z_tag = _strip_tag_namespace(z_elem.tag)
                                if z_tag == 'tatsaechlicherVk':
                                    try:
                                        metrics.total_sales_amount_cents += int((z_elem.text or "0").strip())
                                    except ValueError:
                                        pass
                                elif z_tag == 'verkaufsmenge':
                                    try:
                                        qty = int((z_elem.text or "1").strip())
                                        # Adjust if needed
                                    except ValueError:
                                        pass


def _parse_lagerblock(lagerblock: ET.Element, metrics: ADASMetrics):
    """Processes lagerblock elements and computes stock and expiration KPIs."""
    now_dt = datetime.now(timezone.utc)
    
    for elem in lagerblock:
        tag_name = _strip_tag_namespace(elem.tag)
        if tag_name == 'lager':
            for child in elem:
                c_tag = _strip_tag_namespace(child.tag)
                if c_tag == 'lagerzeile':
                    metrics.total_stock_items += 1
                    for z_elem in child:
                        z_tag = _strip_tag_namespace(z_elem.tag)
                        if z_tag == 'bestand':
                            try:
                                metrics.total_stock_packs += int((z_elem.text or "0").strip())
                            except ValueError:
                                pass
                        elif z_tag == 'fruehesterVerfall':
                            date_str = (z_elem.text or "").strip()
                            if date_str and not date_str.startswith('31.12.9999'):
                                try:
                                    # Format ISO or YYYY-MM-DD
                                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                    days_left = (dt - now_dt).days
                                    if 0 <= days_left <= 90:
                                        metrics.expiring_90d_count += 1
                                    if days_left < -180:
                                        metrics.old_stock_180d_count += 1
                                except Exception:
                                    pass


def _parse_wareneingangsblock(we_block: ET.Element, metrics: ADASMetrics):
    """Processes wareneingangsblock elements."""
    for elem in we_block:
        tag_name = _strip_tag_namespace(elem.tag)
        if tag_name == 'wareneingang':
            metrics.goods_receipts_count += 1
            for child in elem:
                c_tag = _strip_tag_namespace(child.tag)
                if c_tag == 'belegBetrag':
                    try:
                        metrics.goods_receipts_amount_cents += int((child.text or "0").strip())
                    except ValueError:
                        pass
                elif c_tag == 'wareneingangszeile':
                    for z_elem in child:
                        z_tag = _strip_tag_namespace(z_elem.tag)
                        if z_tag == 'liefermenge':
                            try:
                                metrics.goods_receipts_packs += int((z_elem.text or "0").strip())
                            except ValueError:
                                pass


def _parse_retourenblock(ret_block: ET.Element, metrics: ADASMetrics):
    """Processes retourenblock elements."""
    for elem in ret_block:
        tag_name = _strip_tag_namespace(elem.tag)
        if tag_name == 'retoure':
            metrics.returns_count += 1
            for child in elem:
                c_tag = _strip_tag_namespace(child.tag)
                if c_tag == 'retourenzeile':
                    for z_elem in child:
                        z_tag = _strip_tag_namespace(z_elem.tag)
                        if z_tag == 'retourenerstattung':
                            try:
                                metrics.returns_amount_cents += int((z_elem.text or "0").strip())
                            except ValueError:
                                pass


def _parse_neinverkaufsblock(nv_block: ET.Element, metrics: ADASMetrics):
    """Processes neinverkaufsblock elements."""
    for elem in nv_block:
        tag_name = _strip_tag_namespace(elem.tag)
        if tag_name == 'neinverkauf':
            metrics.missed_sales_count += 1
            for child in elem:
                c_tag = _strip_tag_namespace(child.tag)
                if c_tag == 'neinverkaufszeile':
                    for z_elem in child:
                        z_tag = _strip_tag_namespace(z_elem.tag)
                        if z_tag == 'nachfragemenge':
                            try:
                                metrics.missed_sales_requested_packs += int((z_elem.text or "0").strip())
                            except ValueError:
                                pass
