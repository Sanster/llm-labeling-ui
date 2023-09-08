import { Plugin, PluginID } from '@/types/plugin';

const isProduction = process.env.NODE_ENV === 'production';
const base_url = isProduction ? '' : 'http://127.0.0.1:8000/';

export const getEndpoint = (plugin: Plugin | null) => {
  if (!plugin) {
    return base_url + 'api/chat';
  }

  if (plugin.id === PluginID.GOOGLE_SEARCH) {
    return 'api/google';
  }

  return 'api/chat';
};
