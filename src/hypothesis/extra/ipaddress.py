# coding=utf-8
#
# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)
#
# Most of this work is copyright (C) 2013-2015 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# https://github.com/DRMacIver/hypothesis/blob/master/CONTRIBUTING.rst for a
# full list of people who may hold copyright, and consult the git log if you
# need to determine who owns an individual contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.
#
# END HEADER

from __future__ import division, print_function, absolute_import

import ipaddress

from hypothesis.errors import InvalidArgument
from hypothesis.strategies import (
    builds,
    integers,
    just,
    tuples,
    defines_strategy,
    check_valid_interval,
)

__all__ = [
    'ip_address',
    'IPv4Address',
    'IPv6Address',
    'ip_network',
    'IPv4Network',
    'IPv6Network',
]


def check_valid_ip_version(version):
    """Checks that a version is valid (either 4 or 6).

    Otherwise raises ValueError.

    """
    if version in [4, 6]:
        return
    else:
        if version is None:
            raise ValueError('Failed to specify an IP version (4 or 6)')
        else:
            raise ValueError('Expected version 4 or 6 but got %r' % version)


def check_valid_ip_address(value, version):
    """Checks that value is either unspecified, or a valid IP address.

    Otherwise raises InvalidArgument.

    """
    check_valid_ip_version(version)
    if value is None:
        return
    try:
        if version == 4:
            ipaddress.IPv4Address(value)
        else:
            ipaddress.IPv6Address(value)
    except ValueError:
        raise InvalidArgument('Expected an IPv%s address '
                              'but got %r' % (version, value))


def check_valid_ip_network(value, version):
    """Checks that value is either unspecified, or a valid IP network.

    Otherwise raises InvalidArgument.

    """
    check_valid_ip_version(version)
    if value is None:
        return
    try:
        if version == 4:
            ipaddress.IPv4Network(value)
        else:
            ipaddress.IPv6Network(value)
    except ValueError:
        raise InvalidArgument("Expected an IPv%s network "
                              "but got %r" % (version, value))


def get_bounds_of_network(network_str):
    """Gets the bounds of an IP network, returned as (lower, upper)
    integers."""
    network = ipaddress.ip_network(network_str)
    lower = int(network.network_address)
    upper = int(network.network_address) + network.num_addresses - 1
    return (lower, upper)


@defines_strategy
def ip_address(min_address=None, max_address=None, network=None, version=None):
    """Return a strategy which generates IP addresses as strings.

    - If min_address is not None, all addresses will be >= min_address.
    - If max_address is not None, all addresses will be <= max_address.
    - If network is not None, all addresses will fall inside the network.
    - Version must be one of 4 or 6.

    """
    # Choose appropriate types and validation functions depending
    # on the IP address version
    check_valid_ip_version(version)

    if version == 4:
        max_length = 2 ** ipaddress.IPV4LENGTH - 1
        IPAddress = ipaddress.IPv4Address

    elif version == 6:
        max_length = 2 ** ipaddress.IPV6LENGTH - 1
        IPAddress = ipaddress.IPv6Address

    check_valid_ip_address(min_address, version=version)
    check_valid_ip_address(max_address, version=version)
    check_valid_ip_network(network, version=version)

    # Coerce the bounds to integers
    if min_address:
        min_value = int(IPAddress(min_address))
    else:
        min_value = 0

    if max_address:
        max_value = int(IPAddress(max_address))
    else:
        max_value = max_length

    # Check that min_address <= max_address.  This condition passes
    # automatically if either address is defaulted.
    if max_value < min_value:
        raise InvalidArgument('Cannot have max_address=%s < min_address=%s' %
                              (min_address, max_address))

    if network:
        network_min, network_max = get_bounds_of_network(network)
        min_value = max(min_value, network_min)
        max_value = min(max_value, network_max)

    # Check that the network isn't disjoint from [min_address, max_address]
    if max_value < min_value:
        # TODO: put in some proper error messages here.
        raise InvalidArgument()

    return builds(
        IPAddress,
        integers(min_value=min_value, max_value=max_value)
    ).map(str)


@defines_strategy
def IPv4Address(min_address=None, max_address=None, network=None):
    """Return a strategy which generates IPv4 addresses as strings.

    - If min_address is not None, all addresses will be >= min_address.
    - If max_address is not None, all addresses will be <= max_address.
    - If network is not None, all addresses will fall inside the network.

    """
    return ip_address(min_address=min_address,
                      max_address=max_address,
                      network=network,
                      version=4)


@defines_strategy
def IPv6Address(min_address=None, max_address=None, network=None):
    """Return a strategy which generates IPv6 addresses as strings.

    - If min_address is not None, all addresses will be >= min_address.
    - If max_address is not None, all addresses will be <= max_address.
    - If network is not None, all addresses will fall inside the network.

    """
    return ip_address(min_address=min_address,
                      max_address=max_address,
                      network=network,
                      version=6)


def check_valid_netmask_length(value, version):
    """Checks that a netmask length is unspecified, or an appropriate
    length for the given version of IP address.

    Otherwise raises InvalidArgument.

    """
    check_valid_ip_version(version)
    if value is None:
        return

    if version == 4:
        max_length = ipaddress.IPV4LENGTH
    else:
        max_length = ipaddress.IPV6LENGTH

    if not (0 <= int(value) <= max_length):
        raise InvalidArgument('Expected netmask length in [%d, %d], got %r' %
                              (0, max_length, value))


@defines_strategy
def ip_network(min_netmask=None, max_netmask=None, version=None):
    """Return a strategy which generates IP networks as strings.

    - If min_netmask is not None, all networks will have netmask >= min_netmask
    - If max_netmask is not None, all networks will have netmask <= max_netmask
    - Version must be one of 4 or 6.

    """
    check_valid_ip_version(version)
    check_valid_netmask_length(min_netmask, version=version)
    check_valid_netmask_length(max_netmask, version=version)
    check_valid_interval(min_netmask, max_netmask,
                         'min_netmask', 'max_netmask')

    # Choose appropriate default lengths based on the IP version
    if version == 4:
        max_possible_length = ipaddress.IPV4LENGTH
        IPNetwork = ipaddress.IPv4Network

    elif version == 6:
        max_possible_length = ipaddress.IPV6LENGTH
        IPNetwork = ipaddress.IPv6Network

    # If the user supplied bounds on the netmask length, use them here
    if min_netmask:
        min_netmask = int(min_netmask)
    else:
        min_netmask = 0

    if max_netmask:
        max_netmask = int(max_netmask)
    else:
        max_netmask = max_possible_length

    # IPNetwork takes an argument consisting of a tuple, where the first
    # argument is an IP address, and the second is the netmask.  We pass
    # the strict=False argument so that non-zero host bits in the IP address
    # are automatically zeroed.
    return builds(
        IPNetwork,
        tuples(
            ip_address(version=version),
            integers(min_value=min_netmask, max_value=max_netmask)
        ),
        strict=just(False)
    ).map(str)


@defines_strategy
def IPv4Network(min_netmask=None, max_netmask=None):
    """Returns a strategy which generates IPv4 networks as strings.

    - If min_netmask is not None, all networks will have netmask >= min_netmask
    - If max_netmask is not None, all networks will have netmask <= max_netmask

    """
    return ip_network(min_netmask=min_netmask,
                      max_netmask=max_netmask,
                      version=4)


@defines_strategy
def IPv6Network(min_netmask=None, max_netmask=None):
    """Returns a strategy which generates IPv6 networks as strings.

    - If min_netmask is not None, all networks will have netmask >= min_netmask
    - If max_netmask is not None, all networks will have netmask <= max_netmask

    """
    return ip_network(min_netmask=min_netmask,
                      max_netmask=max_netmask,
                      version=6)
