#!/usr/bin/env perl
# cert_nonneg_check.pl
#
# Purpose:
#   Check nonnegativity of coefficients a_{m,k} in
#   Z_m(y)=\sum_k a_{m,k} y^k for m up to a chosen bound.
#
# Recurrence:
#   Z_m - Z_{m-1} - (2y+1)Z_{m-2} + Z_{m-3} + y(y+1)Z_{m-4}=0  (m>=4)
#   => a_{m,k} = a_{m-1,k} + 2 a_{m-2,k-1} + a_{m-2,k}
#                - a_{m-3,k} - a_{m-4,k-1} - a_{m-4,k-2}
#
# Initial values:
#   Z_0 = 1
#   Z_1 = y+1
#   Z_2 = y^2 + 2y + 1
#   Z_3 = y^3 + 3y^2 + 3y + 1

use strict;
use warnings;
use POSIX qw(floor);

sub usage {
    return <<"USAGE";
Usage: perl coeff_nonneg_check.pl [Mmax]

Checks coefficients for m = 0,1,...,Mmax.
Default Mmax = 50.

Exit code 0: all coefficients are nonnegative.
Exit code 1: a negative coefficient is found.
USAGE
}

my $mmax = shift(@ARGV);
if (defined $mmax) {
    unless ($mmax =~ /^\d+$/) {
        die usage();
    }
}
$mmax //= 50;

print "Checking nonnegativity of coefficients up to m = $mmax\n";

my @a; # a[m][k]

# Helper: get coefficient with out-of-range = 0.
sub coeff {
    my ($arr, $k) = @_;
    return 0 if (!defined $arr || $k < 0);
    return $arr->[$k] // 0;
}

# Z0, Z1, Z2, Z3
$a[0] = [1];
$a[1] = [1, 1];
$a[2] = [1, 2, 1];
$a[3] = [1, 3, 3, 1];

for my $m (4 .. $mmax) {
    my $kmax = int(( $m + 3 ) / 2);
    $a[$m] = [];
    for my $k (0 .. $kmax) {
        my $val = coeff($a[$m-1], $k)
                + 2 * coeff($a[$m-2], $k-1)
                + coeff($a[$m-2], $k)
                - coeff($a[$m-3], $k)
                - coeff($a[$m-4], $k-1)
                - coeff($a[$m-4], $k-2);
        $a[$m]->[$k] = $val;
    }
}

my $bad_count = 0;
for my $m (0 .. $mmax) {
    my $kmax = int(( $m + 3 ) / 2);
    for my $k (0 .. $kmax) {
        my $v = $a[$m]->[$k] // 0;
        if ($v < 0) {
            print "Negative coefficient at (m=$m,k=$k): $v\n";
            ++$bad_count;
        }
    }
}

if ($bad_count == 0) {
    print "OK: all checked coefficients are >= 0.\n";
    exit 0;
}

print "FAIL: $bad_count negative coefficients found.\n";
exit 1;
