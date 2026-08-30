with tab2:
    st.header("🎯 Generatore Schedina Multipla Personalizzata")
    
    st.markdown("### 1. Impostazioni Quota Totale e Singola")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        min_acc_odd = st.number_input("Quota Totale MIN", min_value=1.5, max_value=100.0, value=3.0, step=0.5)
    with c2:
        max_acc_odd = st.number_input("Quota Totale MAX", min_value=2.0, max_value=500.0, value=25.0, step=1.0)
    with c3:
        single_min_odd = st.number_input("Quota Singola MIN (x evento)", min_value=1.10, max_value=10.0, value=1.25, step=0.05)
    with c4:
        single_max_odd = st.number_input("Quota Singola MAX (x evento)", min_value=1.20, max_value=20.0, value=4.00, step=0.10)

    st.markdown("### 2. Modalità Numero Eventi")
    mode_eventi = st.radio("Scegli criterio eventi:", ["Range (Min - Max)", "Numero Esatto"], horizontal=True)

    exact_ev = None
    min_ev_cnt = 2
    max_ev_cnt = 6

    if mode_eventi == "Numero Esatto":
        exact_ev = st.number_input("Numero Esatto di Eventi in schedina", min_value=2, max_value=12, value=4, step=1)
    else:
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            min_ev_cnt = st.slider("Numero MIN Eventi", 2, 10, 3)
        with col_e2:
            max_ev_cnt = st.slider("Numero MAX Eventi", 2, 12, 6)

    if st.button("🚀 Calcola Multipla Personalizzata"):
        with st.spinner("Ricerca della combinazione ottimale..."):
            acc = build_accumulator(
                target_min_odds=float(min_acc_odd),
                target_max_odds=float(max_acc_odd),
                min_events=int(min_ev_cnt),
                max_events=int(max_ev_cnt),
                exact_events=exact_ev,
                single_min_odd=float(single_min_odd),
                single_max_odd=float(single_max_odd)
            )
            if acc:
                st.success(f"🎯 Multipla Trovata ({acc['num_events']} eventi)! Quota Totale: {acc['total_odds']} | Probabilità Combinata: {acc['combined_prob']}%")
                df_acc = pd.DataFrame(acc["events"])
                st.dataframe(df_acc[["league", "match", "selection", "odds", "prob", "ev"]], use_container_width=True)
            else:
                st.error("Nessuna combinazione soddisfa i criteri scelti. Prova ad allargare il range della quota totale o ad abbassare la Quota Singola MIN.")
