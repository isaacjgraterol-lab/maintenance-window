from __future__ import annotations

# Table/RIB names are the most reliable source for reporting.  The family label is
# intentionally descriptive and is used only for normalized reports.
BGP_TABLE_FAMILY_MAP: dict[str, str] = {
    "inet.0": "ipv4-unicast",
    "inet6.0": "ipv6-unicast",
    "inet.3": "ipv4-labeled-unicast",
    "inet6.3": "ipv6-labeled-unicast",
    "bgp.l3vpn.0": "vpnv4-unicast",
    "bgp.l3vpn-inet6.0": "vpnv6-unicast",
    "bgp.evpn.0": "evpn",
    "bgp.l2vpn.0": "l2vpn-signaling",
    "bgp.mvpn.0": "mvpn",
    "bgp.rtarget.0": "route-target",
    "bgp.inetsrte.0": "ipv4-segment-routing-te",
    "bgp.transport.3": "bgp-ct / transport",
    "lsdist.0": "traffic-engineering / bgp-ls",
    "inetflow.0": "ipv4-flow",
    "inet6flow.0": "ipv6-flow",
    "IPV4_UNICAST": "ipv4-unicast",
    "IPV6_UNICAST": "ipv6-unicast",
    "IPV4_LABELED_UNICAST": "ipv4-labeled-unicast",
    "IPV6_LABELED_UNICAST": "ipv6-labeled-unicast",
    "L3VPN_IPV4_UNICAST": "vpnv4-unicast",
    "L3VPN_IPV6_UNICAST": "vpnv6-unicast",
    "L2VPN_EVPN": "evpn",
    "L2VPN_VPLS": "l2vpn-signaling",
    "LINK_STATE": "traffic-engineering / bgp-ls",
    "SRTE_POLICY_IPV4": "ipv4-segment-routing-te",
    "BGP_CT": "bgp-ct / transport",
}

BGP_TABLE_FAMILY_SUFFIX_MAP: dict[str, str] = {
    ".inet.0": "vrf-ipv4-unicast",
    ".inet6.0": "vrf-ipv6-unicast",
    ".inet.3": "vrf-ipv4-labeled-unicast",
    ".inet6.3": "vrf-ipv6-labeled-unicast",
    ".evpn.0": "evpn",
}


def family_from_table(table: object | None) -> str:
    """Return a normalized, report-friendly family label for a Junos BGP table."""
    if table is None:
        return "unknown"

    table_text = str(table).strip()
    if not table_text:
        return "unknown"

    exact = BGP_TABLE_FAMILY_MAP.get(table_text) or BGP_TABLE_FAMILY_MAP.get(table_text.upper())
    if exact is not None:
        return exact

    for suffix, family in BGP_TABLE_FAMILY_SUFFIX_MAP.items():
        if table_text.endswith(suffix):
            return family

    return "unknown"
