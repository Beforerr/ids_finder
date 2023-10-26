env-update:
  mamba env update --file environment.yml

env-create:
  mamba env create --file environment.yml --force
  # conda activate $(CONDA_ENV)
  # pip install -e .

kedro-run-candidates:
  kedro run --to-outputs=candidates.sta_tau_60s --from-inputs=sta.feature_tau_60s
  kedro run --to-outputs=candidates.jno_tau_60s --from-inputs=jno.feature_tau_60s
  kedro run --to-outputs=candidates.thb_tau_60s --from-inputs=thb.feature_tau_60s

kedro-run-primary_states:
  kedro run --to-outputs=sta.primary_state_1h 
  kedro run --to-outputs=jno.primary_state_1h
  kedro run --to-outputs=thb.primary_state_1h