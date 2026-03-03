#!/usr/bin/env perl
# branch_root_certificate.pl
#
# Verify two closed-form certificates used in the paper:
#   1) discriminant of c(y)=256 y^3 + 411 y^2 + 165 y + 32 is negative:
#      Disc(c) = b^2 c^2 - 4ac^3 - 4b^3d - 27a^2d^2 + 18abcd = -3^9 * 31^2 * 37
#   2) numeric sign certificate for y_LY in (-1.13446, -1.13445):
#      c(-113446/100000) < 0 < c(-113445/100000)

use strict;
use warnings;
use bigint;

sub usage {
    return <<'USAGE';
Usage: perl branch_root_certificate.pl [--check-disc] [--check-interval]

Checks the branch-cubic certificates used in the paper.
USAGE
}

sub c_num_from_int_num {
    # Input: integer n, representing y = n / 100000
    # Output: numerator of c(y) with denominator 10^15
    my $n = shift;
    my $d = 100000;
    my $d2 = $d * $d;
    my $d3 = $d2 * $d;
    return 256 * $n**3 + 411 * $n**2 * $d + 165 * $n * $d2 + 32 * $d3;
}

my ($check_disc, $check_interval) = (1,1);
for my $arg (@ARGV) {
    if    ($arg eq '--check-disc')      { $check_disc = 1; }
    elsif ($arg eq '--check-interval')  { $check_interval = 1; }
    elsif ($arg eq '--no-disc')         { $check_disc = 0; }
    elsif ($arg eq '--no-interval')     { $check_interval = 0; }
    elsif ($arg =~ /^-+/) { die usage(); }
}

if ($check_disc) {
    my ($a, $b, $c, $d) = (256, 411, 165, 32);
    my $disc = $b*$b*$c*$c - 4*$a*$c*$c*$c - 4*$b*$b*$b*$d - 27*$a*$a*$d*$d + 18*$a*$b*$c*$d;
    my $fact = -3**9 * 31**2 * 37;
    print "disc(c) = $disc\n";
    print "expected = $fact\n";
    if ($disc == $fact) {
        print "OK: disc(c) certificate is exact.\n";
    } else {
        print "ERROR: disc(c) mismatch.\n";
        exit 1;
    }
}

if ($check_interval) {
    my $n_low  = -113446; # y = -113446/100000
    my $n_high = -113445; # y = -113445/100000
    my $c_low  = c_num_from_int_num($n_low);
    my $c_high = c_num_from_int_num($n_high);
    print "c(-113446/100000) = $c_low / 10^15\n";
    print "c(-113445/100000) = $c_high / 10^15\n";

    if ($c_low < 0 && $c_high > 0) {
        print "OK: unique real root lies in (-1.13446, -1.13445) by sign change.\n";
    } else {
        print "ERROR: interval certificate failed.\n";
        exit 1;
    }
}

print "All requested checks passed.\n";
exit 0;
