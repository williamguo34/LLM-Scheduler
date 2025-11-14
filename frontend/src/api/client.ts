import axios from "axios";

import { useSettingsStore } from "../store/useSettingsStore";

const initialBaseUrl = useSettingsStore.getState().apiBaseUrl || "/api";

const client = axios.create({
  baseURL: initialBaseUrl,
  timeout: 60000
});

useSettingsStore.subscribe((state) => {
  client.defaults.baseURL = state.apiBaseUrl || "/api";
});

export default client;
