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
        1: "Common", 2: "Excellent", 3: "Elite", 4: "Epic",
        5: "Legendary", 6: "Mythic", 7: "Mythic*",
        8: "Mythic**", 9: "Mythic***"
    }

    name_to_level = {v.lower(): k for k, v in level_names.items()}

    # --- Shard Calculation ---
    def get_shards(name, level):
        if name in normal_gear:
            return 20 * (2 ** (level - 1))
        else:
            if level < 5:
                return 0
            return 1280 * (2 ** (level - 5))

    # --- Merge System ---
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

    # --- Summon Logic ---
    def summon(inventory, total_summons):
        total_summons += 1

        if total_summons % 50 == 0:
            name = random.choice(special_gear)
            level = 5
        else:
            roll = random.random()

            if roll < 0.50:
                name = random.choice(normal_gear); level = 1
            elif roll < 0.75:
                name = random.choice(normal_gear); level = 2
            elif roll < 0.95:
                name = random.choice(normal_gear); level = 3
            elif roll < 0.975:
                name = random.choice(normal_gear); level = 4
            elif roll < 0.985:
                name = random.choice(normal_gear); level = 5
            elif roll < 0.995:
                name = random.choice(special_gear); level = 4
            else:
                name = random.choice(special_gear); level = 5

        slot = random.choice(gear_slots)
        inventory[(name, slot, level)] += 1

        return total_summons

    # ================= UI =================

    with st.expander("Simulation Settings", expanded=True):
        num_simulations = st.number_input("How many simulations?", min_value=1, value=1)

        mode = st.radio(
            "Which mode would you like to use?",
            ["Run certain amount of summons", "Pick target equipment to summon"]
        )

        if mode == "Run certain amount of summons":
            num_summons = st.number_input("Summons per simulation", min_value=1, value=100)

        else:
            target_name = st.selectbox(
                "Target Gear Name",
                ["Any", "Any S tier"] + all_gear
            )

            target_slot = st.selectbox(
                "Target Slot",
                gear_slots + ["Any", "All"]
            )

            target_level_name = st.selectbox(
                "Target Level",
                list(level_names.values())
            )

            target_level = name_to_level[target_level_name.lower()]

            target_quantity = st.number_input(
                "Quantity needed",
                min_value=1,
                value=1
            )

    # --- Output Filter ---
    with st.expander("Output Filter Options", expanded=True):
        gear_filter = []
        for g in all_gear:
            if st.checkbox(g, value=True):
                gear_filter.append(g)

    # --- Dismantle Options ---
    with st.expander("Dismantle Options"):
        dismantle_filter = []
        for g in all_gear:
            if st.checkbox(f"Dismantle {g}", value=False):
                dismantle_filter.append(g)

    # --- Target Matching ---
    def matches_target(name):
        if target_name == "Any":
            return True
        elif target_name == "Any S tier":
            return name in special_gear
        else:
            return name == target_name

    # ================= RUN =================

    if st.button("▶ Run Simulation"):

        cumulative_inventory = defaultdict(int)
        total_summons_overall = 0
        total_shards = 0

        progress_bar = st.progress(0)

        for sim in range(num_simulations):

            inventory = defaultdict(int)
            total_summons = 0

            if mode == "Run certain amount of summons":

                for _ in range(num_summons):
                    total_summons = summon(inventory, total_summons)

                inventory = merge_inventory(inventory)

            else:

                while True:
                    total_summons = summon(inventory, total_summons)
                    inventory = merge_inventory(inventory)

                    def count_matching(slot_check=None):
                        return sum(
                            v for (n, s, l), v in inventory.items()
                            if matches_target(n)
                            and (slot_check is None or s == slot_check)
                            and l >= target_level
                        )

                    if target_slot == "Any":
                        if count_matching() >= target_quantity:
                            break

                    elif target_slot == "All":
                        if all(count_matching(s) >= target_quantity for s in gear_slots):
                            break

                    else:
                        if count_matching(target_slot) >= target_quantity:
                            break

            # --- Dismantle Step ---
            new_inventory = defaultdict(int)

            for (name, slot, level), count in inventory.items():
                if name in dismantle_filter:
                    total_shards += get_shards(name, level) * count
                else:
                    new_inventory[(name, slot, level)] += count

            for key, value in new_inventory.items():
                cumulative_inventory[key] += value

            total_summons_overall += total_summons

            progress_bar.progress((sim + 1) / num_simulations)

        # --- Averages ---
        avg_inventory = {
            k: v / num_simulations
            for k, v in cumulative_inventory.items()
        }

        avg_summons = total_summons_overall / num_simulations
        avg_shards = total_shards / num_simulations

        # --- Table Output ---
        rows = []

        for (name, slot, level), count in avg_inventory.items():
            if name in gear_filter:
                rows.append({
                    "Gear": name,
                    "Slot": slot,
                    "Level": level_names[level],
                    "Count": count
                })

        df = pd.DataFrame(rows)

        # --- Show summary FIRST ---
        st.markdown("## Simulation Results")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Avg Summons", f"{avg_summons:.2f}")

        with col2:
            st.metric("Equipment Shards", f"{avg_shards:,.2f}")

        # --- Then show table ---
        if not df.empty:

            pivot = df.pivot_table(
                index=["Gear", "Slot"],
                columns="Level",
                values="Count",
                aggfunc="sum",
                fill_value=0
            )

            pivot = pivot.reindex(
                columns=list(level_names.values()),
                fill_value=0
            )

            if num_simulations > 1:
                pivot = pivot.round(2)
            else:
                pivot = pivot.astype(int)

            pivot = pivot.reset_index()

            st.dataframe(pivot, use_container_width=True)


if __name__ == "__main__":
    main()