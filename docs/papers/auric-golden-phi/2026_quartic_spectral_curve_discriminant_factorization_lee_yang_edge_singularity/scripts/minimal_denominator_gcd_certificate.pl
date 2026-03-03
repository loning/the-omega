#!/usr/bin/env perl
# minimal_denominator_gcd_certificate.pl
#
# Exact symbolic certificate of gcd(N,D) in Q(y)[t] for
#   N(t,y)=1+yt+(y^2-y-1)t^2+(y^3-2y)t^3,
#   D(t,y)=1-t-(2y+1)t^2+t^3+y(y+1)t^4.
#
# After changing variable λ=1/t,
#   N_λ(λ,y)=λ^3 N(1/λ,y)
#   Π(λ,y)=λ^4 D(1/λ,y)
# we have
#   Π-λ N_λ = R1
#   R1 + (y+1) N_λ = R2 = y(y+1)^2(y-1).
# Therefore gcd(Π,N_λ)=1 for y∉{-1,0,1}, hence gcd(N,D)=1 there.

use strict;
use warnings;
use bigint;

sub trim {
    my $v = shift;
    my @a = @{$v};
    my $i = $#a;
    while ($i >= 0 && $a[$i] == 0) {
        pop @a;
        --$i;
    }
    return @a ? @a : (0);
}

# y-polynomials are stored ascending in y: [c0,c1,...]
sub ypoly_add {
    my ($a, $b) = @_;
    my $na = $a->@*;
    my $nb = $b->@*;
    my $m = @{$a};
    my $n = @{$b};
    my $d = $m > $n ? $m : $n;
    my @r = (0) x $d;
    for my $i (0 .. $d - 1) {
        my $ai = $i < $m ? $a->[$i] : 0;
        my $bi = $i < $n ? $b->[$i] : 0;
        $r[$i] = $ai + $bi;
    }
    return [trim(\@r)];
}

sub ypoly_sub {
    my ($a, $b) = @_;
    my $m = $a->@*;
    my $n = $b->@*;
    my $d = $m > $n ? $m : $n;
    my @r = (0) x $d;
    for my $i (0 .. $d - 1) {
        my $ai = $i < $m ? $a->[$i] : 0;
        my $bi = $i < $n ? $b->[$i] : 0;
        $r[$i] = $ai - $bi;
    }
    return [trim(\@r)];
}

# Multiply y-polynomial by (a + b y)
sub ypoly_mul_linear {
    my ($p, $a, $b) = @_;
    my $m = $p->@*;
    my @r = (0) x ($m + 1);
    for my $i (0 .. $m - 1) {
        $r[$i]     += $a * $p->[$i];
        $r[$i + 1] += $b * $p->[$i];
    }
    return [trim(\@r)];
}

sub lambda_mul_by_yplus1 {
    my ($P) = @_;
    my @Q;
    for my $i (0 .. $#{$P}) {
        $Q[$i] = ypoly_mul_linear($P->[$i], 1, 1);
    }
    return \@Q;
}

# λ-polynomial subtraction and addition: arrays indexed by λ-degree,
# each coefficient is a y-polynomial.
sub lambda_add {
    my ($A, $B) = @_;
    my $m = $A->@*;
    my $n = $B->@*;
    my $d = $m > $n ? $m : $n;
    my @R = ([(0)]) x $d;
    for my $i (0 .. $d - 1) {
        my $ai = $i < $m ? $A->[$i] : [0];
        my $bi = $i < $n ? $B->[$i] : [0];
        $R[$i] = ypoly_add($ai, $bi);
    }
    my $k = $#R;
    while ($k >= 0 && scalar(@{$R[$k]}) == 1 && $R[$k]->[0] == 0) {
        pop @R;
        --$k;
    }
    return \@R;
}

sub lambda_sub {
    my ($A, $B) = @_;
    my $m = $A->@*;
    my $n = $B->@*;
    my $d = $m > $n ? $m : $n;
    my @R = ([(0)]) x $d;
    for my $i (0 .. $d - 1) {
        my $ai = $i < $m ? $A->[$i] : [0];
        my $bi = $i < $n ? $B->[$i] : [0];
        $R[$i] = ypoly_sub($ai, $bi);
    }
    my $k = $#R;
    while ($k >= 0 && scalar(@{$R[$k]}) == 1 && $R[$k]->[0] == 0) {
        pop @R;
        --$k;
    }
    return \@R;
}

sub ypoly_to_string {
    my ($p) = @_;
    my @c = @$p;
    my $d = $#c;
    my @t;
    for my $i (reverse 0 .. $d) {
        next if $c[$i] == 0;
        if ($i == 0) {
            push @t, "$c[$i]";
        } elsif ($i == 1) {
            if ($c[$i] == 1) { push @t, "y"; }
            elsif ($c[$i] == -1) { push @t, "-y"; }
            else { push @t, $c[$i] . "y"; }
        } else {
            if ($c[$i] == 1) { push @t, "y^$i"; }
            elsif ($c[$i] == -1) { push @t, "-y^$i"; }
            else { push @t, $c[$i] . "y^$i"; }
        }
    }
    return @t ? join(", ", @t) : "0";
}

sub lambda_poly_to_string {
    my ($P) = @_;
    my @s;
    for my $i (reverse 0 .. $#$P) {
        my $coef = ypoly_to_string($P->[$i]);
        next if $coef eq '0';
        if ($i == 0) {
            push @s, "$coef";
        } elsif ($i == 1) {
            push @s, "($coef)\,\lambda";
        } else {
            push @s, "($coef)\,\lambda^$i";
        }
    }
    return @s ? join(" + ", @s) : "0";
}

sub ypoly_eq {
    my ($a, $b) = @_;
    my $m = $a->@*;
    my $n = $b->@*;
    my $d = $m > $n ? $m : $n;
    for my $i (0 .. $d - 1) {
        my $ai = $i < $m ? $a->[$i] : 0;
        my $bi = $i < $n ? $b->[$i] : 0;
        return 0 if $ai != $bi;
    }
    return 1;
}

# N_lambda coefficients in λ: [const, λ, λ^2, λ^3]
my @Nlambda = (
    [0,-2,0,1],   # y^3 - 2y
    [-1,-1,1,0],  # y^2 - y - 1
    [0,1],        # y
    [1],          # 1
);

# Π coefficients in λ: [const, λ, λ^2, λ^3, λ^4]
my @Pi = (
    [0,1,1],      # y^2 + y
    [1],          # 1
    [-1,-2],      # -1 - 2y
    [-1],         # -1
    [1],          # 1
);

# R1 = Π - λ*N_lambda
my @Nlambda_shift = ( [0], @Nlambda );
my $R1 = lambda_sub(
    \@Pi,
    \@Nlambda_shift
);

# R2 = R1 + (y+1)N_lambda
my @Nyplus1 = map { ypoly_mul_linear($_, 1, 1) } @Nlambda;
my $R2 = lambda_add(
    $R1,
    \@Nyplus1
);

my $expected_R2 = [ [0, -1, -1, 1, 1] ];

print "[Minimality certificate]\n";
print "N_lambda(lambda,y) = ";
print lambda_poly_to_string(\@Nlambda), "\n";
print "Pi(lambda,y)     = ";
print lambda_poly_to_string(\@Pi), "\n\n";
print "R1 = Pi - lambda*N_lambda = ";
print lambda_poly_to_string($R1), "\n";
print "R2 = R1 + (y+1)N_lambda = ";
print lambda_poly_to_string($R2), "\n\n";

if (scalar(@$R2) == 1 && ypoly_eq($R2->[0], $expected_R2->[0])) {
    print "PASS: R2 = y*(y+1)^2*(y-1)\n";
    print "Hence gcd(Pi,N_lambda)=1 for y∉{-1,0,1}.\n";
} else {
    print "FAIL: polynomial identity mismatch\n";
    exit 1;
}

exit 0;