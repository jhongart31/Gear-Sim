import streamlit as st
from collections import defaultdict
import random
import pandas as pd

def main():
    st.set_page_config(page_title="Gear Summoner Simulator", layout="wide")
    st.title("Gear Summoner Simulator")

    # --- Gear setup ---
    normal_gear = ["Assassin", "Crusader", "Farmer", "Hunter", "Paladin"]
    special_gear = ["Viking", "King", "Lord"]
    all_gear = normal_gear + special_gear
    gear_slots = ["Helmet", "Armor", "Shoes"]

    level_names = {
        1: "Common",
        2: "Excellent",
        3: "Elite",
        4: "Epic",
        5: "Legendary",
        6: "Mythic",
        7: "Mythic*",
        8: "Mythic**",
        9: "Mythic***"
    }
    name_to_level = {v.lower(): k for k, v in level_names.items()}

    # --- Shard values ---
    def get_shards(name, level):
        if name in normal_gear:
            return 20 * (2 ** (level - 1))
        else:
            if level < 5:
                return 0
            return 1280 * (2 ** (level - 5))

    def merge_inventory(inv):
        merged = True
        while merged:
            merged = False
            new_inv = defaultdict(int)
            for (name, slot, level), count in inv.items():
                if level < 9:
                    pairs = count // 2
                    remainder = count % 2
                    if pairs > 0:
                        new_inv[(name, slot, level + 1)] += pairs
                        merged = True
                    if remainder > 0:
                        new_inv[(name, slot, level)] += remainder
                else:
                    new_inv[(name, slot, level)] += count
            inv = new_inv
        return inv

    def summon(inventory, total_summons):
        total_summons += 1
        if total_summons % 50 == 0:
            name = random.choice(special_gear)
            level = 5
        else:
            roll = random.random()
            if roll < 0.50:
                name = random.choice(normal_gear)
                level = 1
            elif roll < 0.75:
                name = random.choice(normal_gear)
                level = 2
            elif roll < 0.95:
                name = random.choice(normal_gear)
                level = 3
            elif roll < 0.975:
                name = random.choice(normal_gear)
                level = 4
            elif roll < 0.985:
                name = random.choice(normal_gear)
                level = 5
            elif roll < 0.995:
                name = random.choice(special_gear)
                level = 4
            else:
                name = random.choice(special_gear)
                level = 5
        slot = random.choice(gear_slots)
        inventory[(name, slot, level)] += 1
        return total_summons

    # --- UI Inputs ---
    with st.expander("Simulation Settings", expanded=True):
        num_simulations = st.number_input("How many simulations do you want to run?", min_value=1, value=1)

        mode = st.radio(
            "Which mode would you like to use?",
            ["Run certain amount of summons", "Pick target equipment to summon"]
        )

        if mode == "Run certain amount of summons":
            num_summons = st.number_input("Number of summons per simulation?", min_value=1, value=10)
        else:
            target_name = st.selectbox("Target Gear Name", all_gear)
            target_slot = st.selectbox("Target Gear Slot", gear_slots + ["Any","All"])
            target_level_name = st.selectbox("Target Gear Level", list(level_names.values()))
            target_level = name_to_level[target_level_name.lower()]
            target_quantity = st.number_input("How many of this target gear?", min_value=1, value=1)

    # --- Output Filter Options ---
    with st.expander("Output Filter Options", expanded=True):
        st.write("Select which gear to display:")
        gear_filter = []
        for gear_name in all_gear:
            if st.checkbox(gear_name, value=True):
                gear_filter.append(gear_name)

    # --- Dismantle Options ---
    with st.expander("Dismantle Options", expanded=False):
        st.write("Select gear to dismantle into Equipment Shards:")
        dismantle_filter = []
        for gear_name in all_gear:
            if st.checkbox(f"Dismantle {gear_name}", value=False):
                dismantle_filter.append(gear_name)

    # --- Run Simulation ---
    if st.button("▶ Run Simulation"):

        st.write("Simulation running...")
        progress_bar = st.progress(0)

        cumulative_inventory = defaultdict(int)
        total_summons_overall = 0
        total_shards = 0

        for sim in range(num_simulations):
            inventory = defaultdict(int)
            total_summons = 0

            if mode == "Run certain amount of summons":
                for i in range(num_summons):
                    total_summons = summon(inventory, total_summons)
                inventory = merge_inventory(inventory)
            else:
                while True:
                    total_summons = summon(inventory, total_summons)
                    inventory = merge_inventory(inventory)

                    if target_slot == "Any":
                        total = sum(inventory.get((target_name, s, target_level), 0) for s in gear_slots)
                        if total >= target_quantity:
                            break
                    elif target_slot == "All":
                        if all(inventory.get((target_name, s, target_level), 0) >= target_quantity for s in gear_slots):
                            break
                    else:
                        if inventory.get((target_name, target_slot, target_level), 0) >= target_quantity:
                            break

            # --- Dismantle Logic ---
            new_inventory = defaultdict(int)
            sim_shards = 0

            for (name, slot, level), count in inventory.items():
                if name in dismantle_filter:
                    sim_shards += get_shards(name, level) * count
                else:
                    new_inventory[(name, slot, level)] += count

            total_shards += sim_shards

            for key, value in new_inventory.items():
                cumulative_inventory[key] += value

            total_summons_overall += total_summons
            progress_bar.progress((sim + 1)/num_simulations)

        # --- Averages ---
        average_inventory = defaultdict(float)
        for key, value in cumulative_inventory.items():
            average_inventory[key] = value / num_simulations

        average_summons = total_summons_overall / num_simulations
        average_shards = total_shards / num_simulations

        # --- Pivot Table ---
        rows = []
        for (name, slot, level), count in average_inventory.items():
            if name in gear_filter:
                rows.append({
                    "Gear": name,
                    "Slot": slot,
                    "Level": level_names[level],
                    "Count": count
                })

        df = pd.DataFrame(rows)

        if not df.empty:
            pivot_df = df.pivot_table(
                index=["Gear", "Slot"],
                columns="Level",
                values="Count",
                aggfunc="sum",
                fill_value=0
            )

            ordered_levels = list(level_names.values())
            pivot_df = pivot_df.reindex(columns=ordered_levels, fill_value=0)

            pivot_df = pivot_df.round(2) if num_simulations > 1 else pivot_df.astype(int)
            pivot_df = pivot_df.reset_index()

            st.write(f"### Results (avg summons: {average_summons:.2f})")
            st.dataframe(pivot_df, use_container_width=True)

        st.write(f"###  Average Equipment Shards: {average_shards:,.2f}")

if __name__ == "__main__":
    main()