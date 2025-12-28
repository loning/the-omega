from __future__ import annotations

import math


def _fmt(x) -> str:
    try:
        return f"{x:.20f}"
    except Exception:
        return str(x)


def main() -> None:
    """
    Compute the minimal-model geometric values:
      alpha_geo^{-1} = 4*pi^3 + pi^2 + pi
      mu_geo = 6*pi^5
    and compare them to CODATA 2022 central values as recorded in the companion manuscript.
    """
    try:
        import mpmath as mp

        mp.mp.dps = 80
        pi = mp.pi

        alpha_inv_geo = 4 * pi**3 + pi**2 + pi
        mu_geo = 6 * pi**5

        # CODATA 2022 central values (numerical constants as used in the manuscripts).
        alpha_inv_exp = mp.mpf("137.035999177")
        mu_exp = mp.mpf("1836.15267343")

        d_alpha = alpha_inv_geo - alpha_inv_exp
        rel_alpha = d_alpha / alpha_inv_exp

        d_mu = mu_geo - mu_exp
        rel_mu = d_mu / mu_exp

        # Matching inputs in the multiplicative domain used in the impedance viewpoint.
        s_alpha = mp.e**(d_alpha)  # exp(alpha_geo^{-1} - alpha_exp^{-1})
        s_mu = mu_exp / mu_geo

        print("mpmath precision:", mp.mp.dps, "digits")
        print("alpha_inv_geo =", alpha_inv_geo)
        print("alpha_inv_exp =", alpha_inv_exp)
        print("Delta alpha_inv =", d_alpha)
        print("rel error alpha_inv =", rel_alpha)
        print("s_alpha = exp(Delta alpha_inv) =", s_alpha)
        print()
        print("mu_geo =", mu_geo)
        print("mu_exp =", mu_exp)
        print("Delta mu =", d_mu)
        print("rel error mu =", rel_mu)
        print("s_mu = mu_exp/mu_geo =", s_mu)
        return
    except ImportError:
        pass

    # Fallback: float arithmetic (lower precision).
    pi = math.pi
    alpha_inv_geo = 4 * pi**3 + pi**2 + pi
    mu_geo = 6 * pi**5

    alpha_inv_exp = 137.035999177
    mu_exp = 1836.15267343

    d_alpha = alpha_inv_geo - alpha_inv_exp
    rel_alpha = d_alpha / alpha_inv_exp
    s_alpha = math.exp(d_alpha)

    d_mu = mu_geo - mu_exp
    rel_mu = d_mu / mu_exp
    s_mu = mu_exp / mu_geo

    print("float fallback")
    print("alpha_inv_geo =", _fmt(alpha_inv_geo))
    print("alpha_inv_exp =", _fmt(alpha_inv_exp))
    print("Delta alpha_inv =", _fmt(d_alpha))
    print("rel error alpha_inv =", _fmt(rel_alpha))
    print("s_alpha = exp(Delta alpha_inv) =", _fmt(s_alpha))
    print()
    print("mu_geo =", _fmt(mu_geo))
    print("mu_exp =", _fmt(mu_exp))
    print("Delta mu =", _fmt(d_mu))
    print("rel error mu =", _fmt(rel_mu))
    print("s_mu = mu_exp/mu_geo =", _fmt(s_mu))


if __name__ == "__main__":
    main()


