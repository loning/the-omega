#!/usr/bin/env perl
# branch_root_certificate.pl
#
# Verify algebraic certificates used in the paper:
#   1) Disc(c) for c(y)=256 y^3 + 411 y^2 + 165 y + 32 is negative.
#   2) y_LY lies in the rational interval (-1.13446, -1.13445).
#   3) y_EQ is the unique real root of p_eq in (-0.160092, -0.160091),
#      with coprime check Res_y(c(y), p_eq(y)) != 0.

use strict;
use warnings;
use Math::BigRat;
use Math::BigInt;

sub rat {
    my $x = shift;
    return Math::BigRat->new($x);
}

sub norm_coef {
    my $x = shift;
    return rat(0) unless defined($x);
    my $guard = 0;
    while (ref($x) eq 'ARRAY') {
        $guard++;
        die "norm_coef: suspiciously nested coefficient reference\n" if $guard > 16;
        return rat(0) if scalar(@$x) == 0;
        return norm_coef($x->[0]) if scalar(@$x) == 1;
        die "norm_coef: unexpected non-scalar array input\n";
    }
    my $r = ref($x);
    return $x if $r eq 'Math::BigRat';
    return Math::BigRat->new($x) if $r eq 'Math::BigInt';
    return rat($x);
}

sub usage {
    return <<'USAGE';
Usage: perl branch_root_certificate.pl [--check-disc] [--check-interval] [--check-equimodular] [--check-sturm] [--check-coprime]

Checks the branch-cubic and equimodular certificates used in the paper.
Optional flags:
  --check-disc         check Disc(c) exactly
  --check-interval     check y_LY interval certificate
  --check-equimodular  check y_EQ interval certificate
  --check-sturm         run exact Sturm root-count for p_eq (default: on when equimodular checks are requested)
  --check-coprime       check gcd_y( c(y), p_eq(y) ) = 1 via exact resultant
  --no-disc            disable Disc(c) check
  --no-interval        disable y_LY interval check
  --no-equimodular     disable y_EQ interval check
  --no-sturm           disable Sturm root-count check
  --no-coprime         disable coprime check
USAGE
}

sub poly_trim {
    my $p = shift;
    for my $i (0 .. scalar(@$p) - 1) {
        $p->[$i] = norm_coef($p->[$i]);
    }
    while (scalar(@$p) > 1 && $p->[-1]->is_zero()) {
        pop @$p;
    }
    return $p;
}

sub poly_is_zero {
    my $p = shift;
    return 1 unless ref($p) eq 'ARRAY';
    return 1 if scalar(@$p) == 0;
    my $lc = norm_coef($p->[-1]);
    return $lc->is_zero();
}

sub poly_degree {
    my $p = shift;
    return -1 unless ref($p) eq 'ARRAY';
    return scalar(@$p) - 1;
}

sub poly_scale {
    my ($p, $c) = @_;
    return [ map { norm_coef($_) * $c } @$p ];
}

sub poly_negate {
    my $p = shift;
    return [ map { -norm_coef($_) } @$p ];
}

sub poly_add {
    my ($a, $b, $sign) = @_;
    $sign //= 1;
    my $na = scalar(@$a);
    my $nb = scalar(@$b);
    my $d  = ($na > $nb) ? $na : $nb;
    my @r;
    for my $i (0 .. $d - 1) {
        my $ai = ($i < $na) ? norm_coef($a->[$i]) : rat(0);
        my $bi = ($i < $nb) ? norm_coef($b->[$i]) : rat(0);
        $r[$i] = $ai + $sign * $bi;
    }
    return poly_trim(\@r);
}

sub poly_sub {
    my ($a, $b) = @_;
    return poly_add($a, $b, -1);
}

sub poly_derivative {
    my $p = shift;
    my $n = poly_degree($p);
    return [rat(0)] if $n == 0;
    my @d;
    for my $i (1 .. $n) {
        $d[$i - 1] = $p->[$i] * $i;
    }
    return poly_trim(\@d);
}

sub poly_copy {
    my $p = shift;
    return [ @$p ];
}

sub poly_divmod {
    my ($A, $B) = @_;
    my @R = map { norm_coef($_) } @$A;
    my @Q;
    my $degB = poly_degree($B);
    my $lcB  = $B->[$degB];

    while (!poly_is_zero(\@R) && (poly_degree(\@R) >= $degB)) {
        my $degR = poly_degree(\@R);
        my $degDiff = $degR - $degB;
        my $factor = $R[$degR] / $lcB;
        $Q[$degDiff] = ($Q[$degDiff] // rat(0)) + $factor;

        for my $i (0 .. $degB) {
            my $idx = $i + $degDiff;
            my $sub = $factor * $B->[$i];
            $R[$idx] = norm_coef($R[$idx]) - $sub;
        }

        poly_trim(\@R);
    }

    return (poly_trim(\@Q), poly_trim(\@R));
}

sub poly_sturm_sequence {
    my $p = shift;
    my @S;
    my $dp = poly_copy($p);
    poly_trim(\@$dp);
    push @S, $dp;

    my $dp1 = poly_derivative($dp);
    push @S, $dp1;
    return \@S if poly_is_zero($dp1);

    while (1) {
        my ($q, $r) = poly_divmod($S[-2], $S[-1]);
        last if poly_is_zero($r);
        my $next = poly_negate($r);
        push @S, $next;
    }
    return \@S;
}

sub poly_sign {
    my $x = shift;
    my $c = norm_coef($x)->bcmp(0);
    return 0 if $c == 0;
    return ($c > 0) ? 1 : -1;
}

sub poly_eval {
    my ($p, $x) = @_;
    my $val = rat(0);
    for (my $i = poly_degree($p); $i >= 0; --$i) {
        $val = $val * $x + $p->[$i];
    }
    return $val;
}

sub poly_sign_at_infty {
    my ($p, $sign_x) = @_;
    return 0 if poly_is_zero($p);
    my $sgn = poly_sign($p->[-1]);
    my $d = poly_degree($p);
    if (($d % 2 == 1) && ($sign_x < 0)) {
        $sgn = -$sgn;
    }
    return $sgn;
}

sub poly_sign_variation {
    my ($seq, $x) = @_;
    my @sgn;
    for my $p (@$seq) {
        my $v = poly_sign(poly_eval($p, $x));
        push @sgn, $v if $v != 0;
    }
    return 0 if scalar(@sgn) < 2;
    my $v = 0;
    for my $i (1 .. scalar(@sgn) - 1) {
        $v++ if $sgn[$i] != $sgn[$i - 1];
    }
    return $v;
}

sub poly_sign_variation_infty {
    my ($seq, $sign_x) = @_;
    my @sgn;
    for my $p (@$seq) {
        my $v = poly_sign_at_infty($p, $sign_x);
        push @sgn, $v if $v != 0;
    }
    return 0 if scalar(@sgn) < 2;
    my $v = 0;
    for my $i (1 .. scalar(@sgn) - 1) {
        $v++ if $sgn[$i] != $sgn[$i - 1];
    }
    return $v;
}

sub sturm_real_root_count {
    my $p = shift;
    my $seq = poly_sturm_sequence($p);
    my $v_minus_inf = poly_sign_variation_infty($seq, -1);
    my $v_plus_inf  = poly_sign_variation_infty($seq,  1);
    return $v_minus_inf - $v_plus_inf;
}

sub det_bareiss {
    my $M = shift;
    my $n = scalar(@$M);
    return Math::BigInt->new(0) if $n == 0;

    my $sign = 1;
    my @a = map { [ map { Math::BigInt->new($_) } @$_ ] } @$M;
    my $prev = Math::BigInt->new(1);

    for my $k (0 .. $n - 2) {
        if ($a[$k][$k]->is_zero()) {
            my $pivot_row = -1;
            for my $r ($k + 1 .. $n - 1) {
                if (!$a[$r][$k]->is_zero()) {
                    $pivot_row = $r;
                    last;
                }
            }
            if ($pivot_row == -1) {
                return Math::BigInt->new(0);
            }
            my @tmp = @{$a[$k]};
            @{$a[$k]} = @{$a[$pivot_row]};
            @{$a[$pivot_row]} = @tmp;
            $sign = -$sign;
        }

        my $pivot = $a[$k][$k];
        for my $i ($k + 1 .. $n - 1) {
            for my $j ($k + 1 .. $n - 1) {
                my $num = $a[$i][$j] * $pivot - $a[$i][$k] * $a[$k][$j];
                $num->bdiv($prev);
                $a[$i][$j] = $num;
            }
            for my $j (0 .. $k) {
                $a[$i][$j] = Math::BigInt->new(0);
            }
        }
        $prev = $pivot;
    }

    my $det = $a[$n - 1][$n - 1];
    $det = $det->copy()->bneg() if $sign < 0;
    return $det;
}

sub poly_resultant_int {
    my ($A, $B) = @_;
    my @a = @$A;
    my @b = @$B;

    my $na = scalar(@a) - 1;
    my $nb = scalar(@b) - 1;
    my $size = $na + $nb;

    my @A_desc = reverse @a;
    my @B_desc = reverse @b;

    my @M;

    for my $row (0 .. $nb - 1) {
        my @r = ((0) x $size);
        for my $j (0 .. $na) {
            $r[$j + $row] = $A_desc[$j];
        }
        push @M, [@r];
    }

    for my $row (0 .. $na - 1) {
        my @r = ((0) x $size);
        for my $j (0 .. $nb) {
            $r[$j + $row] = $B_desc[$j];
        }
        push @M, [@r];
    }

    return det_bareiss(\@M);
}

sub c_from_int_num {
    # Input: integer n, representing y = n / 100000
    my $n = shift;
    my $d = 100000;
    my $d2 = $d * $d;
    my $d3 = $d2 * $d;
    my $nn = Math::BigInt->new($n);
    my $num = 256 * ($nn**3) + 411 * ($nn**2) * $d + 165 * $nn * $d2 + 32 * $d3;
    return $num;
}

sub p_eq_num_from_int_num {
    # Input: integer n, representing y = n / 10^6
    my $n = shift;
    my $d = 10**6;
    my @coeff_desc = (256, 1219, 2542, 3090, 2446, 1315, 478, 112, 16, 1); # y^9 ... y^0
    my $den_pow = Math::BigInt->new(1);
    my $num = Math::BigInt->new(0);
    for my $c (@coeff_desc) {
        $num = $num * Math::BigInt->new($n) + (Math::BigInt->new($c) * $den_pow);
        $den_pow *= $d;
    }
    return $num;
}

sub poly_string {
    my $p = shift;
    my $strs = [];
    for my $i (reverse 0 .. poly_degree($p)) {
        my $c = $p->[$i];
        next if $c->is_zero();
        my $cs = $c->bstr();
        my $term;
        if ($i == 0) {
            $term = $cs;
        } elsif ($i == 1) {
            $term = "${cs} y";
        } else {
            $term = "${cs} y^$i";
        }
        push @$strs, $term;
    }
    return scalar(@$strs) ? join(" + ", @$strs) : "0";
}

my $check_disc      = 1;
my $check_interval  = 1;
my $check_equimod   = 1;
my $check_sturm     = 0;
my $check_coprime   = 0;

for my $arg (@ARGV) {
    if    ($arg eq '--check-disc')         { $check_disc = 1; }
    elsif ($arg eq '--check-interval')     { $check_interval = 1; }
    elsif ($arg eq '--check-equimodular')  { $check_equimod = 1; }
    elsif ($arg eq '--check-sturm')        { $check_sturm = 1; }
    elsif ($arg eq '--check-coprime')      { $check_coprime = 1; }
    elsif ($arg eq '--no-disc')            { $check_disc = 0; }
    elsif ($arg eq '--no-interval')        { $check_interval = 0; }
    elsif ($arg eq '--no-equimodular')     { $check_equimod = 0; }
    elsif ($arg eq '--no-sturm')           { $check_sturm = 0; }
    elsif ($arg eq '--no-coprime')         { $check_coprime = 0; }
    elsif ($arg =~ /^-+/)                  { die usage(); }
}

# default Sturm check when equimodular is requested
$check_sturm = 1 if ($check_equimod && !$check_sturm && !grep { /^--no-sturm$/ } @ARGV);

# polynomials in y, ascending coefficients
my $c_poly = [ rat(32), rat(165), rat(411), rat(256) ];
my @c_poly_int = (32, 165, 411, 256);
my $p_eq   = [
    rat(1),   rat(16),   rat(112),  rat(478),
    rat(1315), rat(2446), rat(3090), rat(2542),
    rat(1219), rat(256)
];
my @p_eq_int = (1, 16, 112, 478, 1315, 2446, 3090, 2542, 1219, 256);

if ($check_disc) {
    my ($a, $b, $c, $d) = (256, 411, 165, 32);
    my $disc = $b * $b * $c * $c - 4 * $a * $c * $c * $c - 4 * $b * $b * $b * $d - 27 * $a * $a * $d * $d + 18 * $a * $b * $c * $d;
    my $fact = -(3**9) * (31**2) * 37;
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
    my $c_low  = c_from_int_num($n_low);
    my $c_high = c_from_int_num($n_high);
    print "c(-113446/100000) = $c_low / 10^15\n";
    print "c(-113445/100000) = $c_high / 10^15\n";

    if ($c_low < 0 && $c_high > 0) {
        print "OK: unique real root lies in (-1.13446, -1.13445) by sign change.\n";
    } else {
        print "ERROR: interval certificate failed.\n";
        exit 1;
    }
}

if ($check_equimod) {
    my $n_low  = -160092; # y = -160092/10^6
    my $n_high = -160091; # y = -160091/10^6
    my $peq_low  = p_eq_num_from_int_num($n_low);
    my $peq_high = p_eq_num_from_int_num($n_high);
    print "p_eq(-160092/10^6) = $peq_low / 10^54\n";
    print "p_eq(-160091/10^6) = $peq_high / 10^54\n";

    if ($peq_low < 0 && $peq_high > 0) {
        print "OK: p_eq(y_EQ) has an odd-numbered real root in (-160092/10^6, -160091/10^6).\n";
        if ($check_sturm) {
            my $roots = sturm_real_root_count($p_eq);
            print "Sturm root count for p_eq on R: $roots\n";
            if ($roots == 1) {
                print "OK: Sturm certificate proves p_eq has exactly one real root.\n";
            } else {
                print "ERROR: Sturm count expects one real root for p_eq.\n";
                exit 1;
            }
        }
        if ($check_coprime) {
            my $res = poly_resultant_int(\@c_poly_int, \@p_eq_int);
            if (!$res->is_zero()) {
                print "OK: Res_y(c(y), p_eq(y)) is nonzero, so gcd(c(y), p_eq(y)) = 1.\n";
            } else {
                print "ERROR: Res_y(c(y), p_eq(y)) = 0, so gcd(c(y), p_eq(y)) != 1.\n";
                exit 1;
            }
        }
    } else {
        print "ERROR: equimodular interval certificate failed.\n";
        exit 1;
    }
}

print "All requested checks passed.\n";
exit 0;
