import { Conversation, Message } from '@/types/chat';
import { ErrorMessage } from '@/types/error';
import { FolderInterface } from '@/types/folder';
import { OpenAIModel, OpenAIModelID } from '@/types/openai';
import { PluginKey } from '@/types/plugin';
import { Prompt } from '@/types/prompt';

export const MESSAGE_FILTER_NONE = 'message-count-none';
export const MESSAGE_FILTER_EQUAL = 'message-count-equal';
export const MESSAGE_FILTER_GREATER = 'message-count-greater';
export const MESSAGE_FILTER_LESS = 'message-count-less';

export interface HomeInitialState {
  apiKey: string;
  apiOrg: string;
  pluginKeys: PluginKey[];
  loading: boolean;
  lightMode: 'light' | 'dark';
  messageIsStreaming: boolean;
  modelError: ErrorMessage | null;
  models: OpenAIModel[];
  folders: FolderInterface[];
  conversations: Conversation[];
  selectedConversation: Conversation | undefined;
  selectedConversationPageIndex: number | undefined;
  currentMessage: Message | undefined;
  prompts: Prompt[];
  temperature: number;
  showChatbar: boolean;
  showPromptbar: boolean;
  currentFolder: FolderInterface | undefined;
  messageError: boolean;
  searchTerm: string;
  messageCountFilterCount: number;
  messageCountFilterMode: string;
  defaultModelId: OpenAIModelID | undefined;
  serverSideApiKeyIsSet: boolean;
  serverSidePluginKeysSet: boolean;
  page: number;
  pageBeforeSearch: number | null;
  selectedConversationPageIndexBeforeSearch: number | null;
  totalPages: number;
  totalConversations: number;
}

export const initialState: HomeInitialState = {
  apiKey: '',
  apiOrg: '',
  loading: false,
  pluginKeys: [],
  lightMode: 'dark',
  messageIsStreaming: false,
  modelError: null,
  models: [],
  folders: [],
  conversations: [],
  selectedConversation: undefined,
  selectedConversationPageIndex: undefined,
  currentMessage: undefined,
  prompts: [],
  temperature: 1,
  showPromptbar: true,
  showChatbar: true,
  currentFolder: undefined,
  messageError: false,
  searchTerm: '',
  messageCountFilterCount: 0,
  messageCountFilterMode: MESSAGE_FILTER_NONE,
  defaultModelId: undefined,
  serverSideApiKeyIsSet: false,
  serverSidePluginKeysSet: false,
  page: 0,
  pageBeforeSearch: null,
  selectedConversationPageIndexBeforeSearch: null,
  totalPages: 1,
  totalConversations: 0,
};
