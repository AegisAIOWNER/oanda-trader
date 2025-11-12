#!/usr/bin/env python
"""
Demo script showing auto-scaling position sizing in action.
This demonstrates how the feature adapts to different account states and constraints.
"""

from position_sizing import PositionSizer


def print_scenario(title, result_dict):
    """Pretty print a scenario result."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    
    units = result_dict['units']
    risk_pct = result_dict['risk_pct']
    debug_info = result_dict['debug_info']
    
    if units == 0:
        print(f"❌ TRADE SKIPPED")
        print(f"   Reason: {debug_info.get('skip_reason', 'Unknown')}")
        if 'available_margin' in debug_info:
            print(f"   Available Margin: ${debug_info['available_margin']:.2f}")
        if 'minimum_trade_size' in debug_info:
            print(f"   Minimum Required: {debug_info['minimum_trade_size']}")
    else:
        print(f"✅ TRADE APPROVED")
        print(f"   Final Units: {units:,}")
        print(f"   Risk %: {risk_pct*100:.2f}%")
        print(f"\n   Constraints:")
        print(f"   - Units by Margin: {debug_info.get('units_by_margin', 'N/A'):,}")
        print(f"   - Units by Risk: {debug_info.get('units_by_risk', 'N/A'):,}")
        print(f"   - Limiting Factor: {'MARGIN' if units <= debug_info.get('units_by_margin', float('inf')) else 'RISK'}")
        print(f"\n   Details:")
        print(f"   - Effective Margin: ${debug_info.get('effective_available_margin', 0):.2f}")
        print(f"   - Trade Value: ${debug_info.get('trade_value', 0):.2f}")
        print(f"   - Risk Amount: ${debug_info.get('actual_risk_amount', 0):.2f}")


def run_demo():
    """Run demonstration scenarios."""
    print("\n" + "="*70)
    print("  AUTO-SCALING POSITION SIZING DEMONSTRATION")
    print("="*70)
    
    sizer = PositionSizer(
        method='fixed_percentage',
        risk_per_trade=0.02,
        min_trade_value=1.50
    )
    
    # Scenario 1: Healthy account with good margin
    units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
        balance=10000.0,
        available_margin=9000.0,
        current_price=1.1000,
        stop_loss_pips=15.0,
        pip_value=0.0001,
        margin_rate=0.0333,
        auto_scale_margin_buffer=0.0,
        minimum_trade_size=1,
        trade_units_precision=0,
        maximum_order_units=100000000,
        max_units_per_instrument=100000
    )
    print_scenario(
        "Scenario 1: Healthy Account - Plenty of Margin",
        {'units': units, 'risk_pct': risk_pct, 'debug_info': debug_info}
    )
    
    # Scenario 2: Low margin situation
    units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
        balance=10000.0,
        available_margin=500.0,  # Very low margin
        current_price=1.1000,
        stop_loss_pips=15.0,
        pip_value=0.0001,
        margin_rate=0.0333,
        auto_scale_margin_buffer=0.0,
        minimum_trade_size=1,
        trade_units_precision=0,
        maximum_order_units=100000000,
        max_units_per_instrument=100000
    )
    print_scenario(
        "Scenario 2: Low Margin - Constrained by Available Funds",
        {'units': units, 'risk_pct': risk_pct, 'debug_info': debug_info}
    )
    
    # Scenario 3: With margin buffer for safety
    units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
        balance=10000.0,
        available_margin=5000.0,
        current_price=1.1000,
        stop_loss_pips=15.0,
        pip_value=0.0001,
        margin_rate=0.0333,
        auto_scale_margin_buffer=0.5,  # 50% buffer!
        minimum_trade_size=1,
        trade_units_precision=0,
        maximum_order_units=100000000,
        max_units_per_instrument=100000
    )
    print_scenario(
        "Scenario 3: Safety-First - 50% Margin Buffer Applied",
        {'units': units, 'risk_pct': risk_pct, 'debug_info': debug_info}
    )
    
    # Scenario 4: High risk per unit (wide stop)
    units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
        balance=10000.0,
        available_margin=9000.0,
        current_price=1.1000,
        stop_loss_pips=100.0,  # Very wide stop = high risk per unit
        pip_value=0.0001,
        margin_rate=0.0333,
        auto_scale_margin_buffer=0.0,
        minimum_trade_size=1,
        trade_units_precision=0,
        maximum_order_units=100000000,
        max_units_per_instrument=100000
    )
    print_scenario(
        "Scenario 4: Wide Stop - Risk Becomes Limiting Factor",
        {'units': units, 'risk_pct': risk_pct, 'debug_info': debug_info}
    )
    
    # Scenario 5: Insufficient margin (trade skip)
    units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
        balance=100.0,
        available_margin=10.0,  # Almost no margin
        current_price=1.1000,
        stop_loss_pips=15.0,
        pip_value=0.0001,
        margin_rate=0.0333,
        auto_scale_margin_buffer=0.0,
        minimum_trade_size=1000,  # High minimum
        trade_units_precision=0,
        maximum_order_units=100000000,
        max_units_per_instrument=100000
    )
    print_scenario(
        "Scenario 5: Insufficient Margin - Trade Skipped",
        {'units': units, 'risk_pct': risk_pct, 'debug_info': debug_info}
    )
    
    # Scenario 6: High leverage instrument
    units, risk_pct, debug_info = sizer.calculate_auto_scaled_units(
        balance=10000.0,
        available_margin=9000.0,
        current_price=1.1000,
        stop_loss_pips=15.0,
        pip_value=0.0001,
        margin_rate=0.02,  # 50:1 leverage (vs 30:1)
        auto_scale_margin_buffer=0.0,
        minimum_trade_size=1,
        trade_units_precision=0,
        maximum_order_units=100000000,
        max_units_per_instrument=100000
    )
    print_scenario(
        "Scenario 6: High Leverage (50:1) - More Units Possible",
        {'units': units, 'risk_pct': risk_pct, 'debug_info': debug_info}
    )
    
    print(f"\n{'='*70}")
    print("  DEMONSTRATION COMPLETE")
    print(f"{'='*70}\n")
    print("Key Takeaways:")
    print("1. Auto-scaling adapts position size to available margin")
    print("2. Risk limits (2%) are always respected")
    print("3. Trades are skipped with clear reasons when constraints can't be met")
    print("4. Margin buffers provide extra safety cushion")
    print("5. Both margin AND risk constraints are considered")
    print("6. The most restrictive constraint determines final position size")
    print()


if __name__ == '__main__':
    run_demo()
