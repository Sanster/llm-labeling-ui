'use client';

import { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { useQuery } from 'react-query';

import { useTranslation } from 'next-i18next';
import Head from 'next/head';

import { useCreateReducer } from '@/hooks/useCreateReducer';
import { useFetch } from '@/hooks/useFetch';

import useErrorService from '@/services/errorService';
import useApiService from '@/services/useApiService';

import HomeContext from '../utils/home.context';
import {
  cleanConversationHistory,
  cleanSelectedConversation,
} from '@/utils/app/clean';
import { DEFAULT_SYSTEM_PROMPT, DEFAULT_TEMPERATURE } from '@/utils/app/const';
import {
  saveConversation,
  saveConversations,
  updateConversation,
} from '@/utils/app/conversation';
import { saveFolders } from '@/utils/app/folders';
import { savePrompts } from '@/utils/app/prompts';
import { getSettings } from '@/utils/app/settings';
import { HomeInitialState, initialState } from '@/utils/home.state';

import { Conversation } from '@/types/chat';
import { KeyValuePair } from '@/types/data';
import { FolderInterface, FolderType } from '@/types/folder';
import { OpenAIModelID, OpenAIModels, fallbackModelID } from '@/types/openai';
import { Prompt } from '@/types/prompt';

import { Chat } from '@/components/Chat/Chat';
import { Chatbar } from '@/components/Chatbar/Chatbar';
import Promptbar from '@/components/Promptbar';

// import { Navbar } from '@/components/Mobile/Navbar';
// import Promptbar from '@/components/Promptbar';
import { v4 as uuidv4 } from 'uuid';

const Home = () => {
  const serverSideApiKeyIsSet = false;
  const serverSidePluginKeysSet = false;
  const defaultModelId = OpenAIModelID.GPT_3_5;
  const { t } = useTranslation('chat');
  const { getModels, getConversations } = useApiService();
  const { getModelsError } = useErrorService();
  const fetchService = useFetch();
  const [initialRender, setInitialRender] = useState<boolean>(true);

  const contextValue = useCreateReducer<HomeInitialState>({
    initialState,
  });

  const {
    state: {
      apiKey,
      apiOrg,
      lightMode,
      folders,
      conversations,
      selectedConversation,
      selectedConversationPageIndex,
      prompts,
      page,
      searchTerm,
      totalPages,
    },
    dispatch,
  } = contextValue;

  const stopConversationRef = useRef<boolean>(false);

  const { data, error, refetch } = useQuery(
    ['GetModels', apiKey, apiOrg, serverSideApiKeyIsSet],
    ({ signal }) => {
      if (!apiKey && !serverSideApiKeyIsSet) return null;

      return getModels(
        {
          key: apiKey,
          org: apiOrg,
        },
        signal,
      );
    },
    { enabled: true, refetchOnMount: false },
  );

  useEffect(() => {
    if (data) dispatch({ field: 'models', value: data });
  }, [data, dispatch]);

  const {
    data: conversationsData,
    error: conversationsError,
    refetch: refetchConversations,
  } = useQuery(
    ['GetConversations', page, searchTerm, 15],
    ({ signal }) => {
      console.log(`fetch conversations ${page}, ${searchTerm}`);
      return getConversations(
        {
          page: page,
          pageSize: 15,
          searchTerm: searchTerm,
        },
        signal,
      );
    },
    { enabled: true, refetchOnMount: false, refetchOnWindowFocus: false },
  );

  useEffect(() => {
    var convs = conversationsData?.conversations?.map((c) => c.data);
    if (convs) {
      convs = convs.reverse();
      // 正确设置 selectedConversation，要考虑删除、创建的情况
      if (convs.length === 0) {
        dispatch({
          field: 'selectedConversation',
          value: undefined,
        });
      } else {
        let convPageIndex: number =
          selectedConversationPageIndex === undefined
            ? convs.length - 1
            : convs.length - selectedConversationPageIndex - 1;
        if (convPageIndex < 0) {
          convPageIndex = 0;
        }
        if (convPageIndex >= convs.length) {
          convPageIndex = convs.length - 1;
        }
        if (convs[convPageIndex].id !== selectedConversation?.id) {
          dispatch({
            field: 'selectedConversation',
            value: convs[convPageIndex],
          });
        }
      }
      dispatch({ field: 'conversations', value: convs });
      dispatch({ field: 'totalPages', value: conversationsData?.totalPages });
      dispatch({
        field: 'totalConversations',
        value: conversationsData?.totalConversations,
      });
    }
  }, [conversationsData, dispatch]);

  // 不注释这个会导致无限循环
  // useEffect(() => {
  //   dispatch({ field: 'modelError', value: getModelsError(error) });
  // }, [dispatch, error, getModelsError]);

  // FETCH MODELS ----------------------------------------------

  const handleSelectConversation = (
    conversation: Conversation,
    conversationPageIndex: number,
  ) => {
    dispatch({
      field: 'selectedConversation',
      value: conversation,
    });
    dispatch({
      field: 'selectedConversationPageIndex',
      value: conversationPageIndex,
    });

    saveConversation(conversation);
  };

  // FOLDER OPERATIONS  --------------------------------------------

  const handleCreateFolder = (name: string, type: FolderType) => {
    const newFolder: FolderInterface = {
      id: uuidv4(),
      name,
      type,
    };

    const updatedFolders = [...folders, newFolder];

    dispatch({ field: 'folders', value: updatedFolders });
    saveFolders(updatedFolders);
  };

  const handleDeleteFolder = (folderId: string) => {
    const updatedFolders = folders.filter((f) => f.id !== folderId);
    dispatch({ field: 'folders', value: updatedFolders });
    saveFolders(updatedFolders);

    const updatedConversations: Conversation[] = conversations.map((c) => {
      if (c.folderId === folderId) {
        return {
          ...c,
          folderId: null,
        };
      }

      return c;
    });

    dispatch({ field: 'conversations', value: updatedConversations });
    saveConversations(updatedConversations);

    const updatedPrompts: Prompt[] = prompts.map((p) => {
      if (p.folderId === folderId) {
        return {
          ...p,
          folderId: null,
        };
      }

      return p;
    });

    dispatch({ field: 'prompts', value: updatedPrompts });
    savePrompts(updatedPrompts);
  };

  const handleUpdateFolder = (folderId: string, name: string) => {
    const updatedFolders = folders.map((f) => {
      if (f.id === folderId) {
        return {
          ...f,
          name,
        };
      }

      return f;
    });

    dispatch({ field: 'folders', value: updatedFolders });

    saveFolders(updatedFolders);
  };

  // CONVERSATION OPERATIONS  --------------------------------------------

  const handleNewConversation = async () => {
    const lastConversation = conversations[conversations.length - 1];

    const newConversation: Conversation = {
      id: uuidv4(),
      name: t('New Conversation'),
      messages: [],
      model: lastConversation?.model || {
        id: OpenAIModels[defaultModelId].id,
        name: OpenAIModels[defaultModelId].name,
        maxLength: OpenAIModels[defaultModelId].maxLength,
        tokenLimit: OpenAIModels[defaultModelId].tokenLimit,
      },
      prompt: DEFAULT_SYSTEM_PROMPT,
      temperature: lastConversation?.temperature ?? DEFAULT_TEMPERATURE,
      folderId: null,
    };

    try {
      const res = await fetchService.post<Conversation>(
        '/api/create_conversation',
        {
          body: newConversation,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    } catch (e) {
      toast.error(`${e}`);
      return;
    }

    dispatch({ field: 'page', value: 0 });
    dispatch({ field: 'selectedConversationPageIndex', value: 0 });
    refetchConversations();

    // const updatedConversations = [...conversations, newConversation];

    // dispatch({ field: 'selectedConversation', value: newConversation });
    // dispatch({ field: 'conversations', value: updatedConversations });

    // saveConversation(newConversation);
    // saveConversations(updatedConversations);

    dispatch({ field: 'loading', value: false });
  };

  const handleUpdateConversation = async (
    conversation: Conversation,
    data: KeyValuePair,
  ) => {
    const updatedConversation = {
      ...conversation,
      [data.key]: data.value,
    };

    try {
      const res = await fetchService.post<Conversation>(
        '/api/update_conversation',
        {
          body: updatedConversation,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    } catch (e) {
      toast.error(`${e}`);
      return;
    }

    const { single, all } = updateConversation(
      updatedConversation,
      conversations,
    );

    dispatch({ field: 'selectedConversation', value: single });
    dispatch({ field: 'conversations', value: all });
  };

  const handleDeleteConversation = async (conversation: Conversation) => {
    try {
      const res = await fetchService.post<Conversation>(
        '/api/delete_conversation',
        {
          body: conversation,
          headers: {
            'Content-Type': 'application/json',
          },
        },
      );
    } catch (e) {
      alert(e);
      return;
    }

    refetchConversations();
  };

  // EFFECTS  --------------------------------------------

  useEffect(() => {
    if (window.innerWidth < 640) {
      dispatch({ field: 'showChatbar', value: false });
    }
  }, [selectedConversation]);

  useEffect(() => {
    defaultModelId &&
      dispatch({ field: 'defaultModelId', value: defaultModelId });
    serverSideApiKeyIsSet &&
      dispatch({
        field: 'serverSideApiKeyIsSet',
        value: serverSideApiKeyIsSet,
      });
    serverSidePluginKeysSet &&
      dispatch({
        field: 'serverSidePluginKeysSet',
        value: serverSidePluginKeysSet,
      });
  }, [defaultModelId, serverSideApiKeyIsSet, serverSidePluginKeysSet]);

  // ON LOAD --------------------------------------------

  useEffect(() => {
    const settings = getSettings();
    if (settings.theme) {
      dispatch({
        field: 'lightMode',
        value: settings.theme,
      });
    }

    const apiKey = localStorage.getItem('apiKey');

    if (serverSideApiKeyIsSet) {
      dispatch({ field: 'apiKey', value: '' });

      localStorage.removeItem('apiKey');
    } else if (apiKey) {
      dispatch({ field: 'apiKey', value: apiKey });
    }

    const apiOrg = localStorage.getItem('apiOrg');
    if (apiOrg) {
      dispatch({ field: 'apiOrg', value: apiOrg });
    } else {
      dispatch({ field: 'apiOrg', value: '' });
    }

    const pluginKeys = localStorage.getItem('pluginKeys');
    if (serverSidePluginKeysSet) {
      dispatch({ field: 'pluginKeys', value: [] });
      localStorage.removeItem('pluginKeys');
    } else if (pluginKeys) {
      dispatch({ field: 'pluginKeys', value: pluginKeys });
    }

    if (window.innerWidth < 640) {
      dispatch({ field: 'showChatbar', value: false });
      dispatch({ field: 'showPromptbar', value: false });
    }

    const showChatbar = localStorage.getItem('showChatbar');
    if (showChatbar) {
      dispatch({ field: 'showChatbar', value: showChatbar === 'true' });
    }

    const showPromptbar = localStorage.getItem('showPromptbar');
    if (showPromptbar) {
      dispatch({ field: 'showPromptbar', value: showPromptbar === 'true' });
    }

    const folders = localStorage.getItem('folders');
    if (folders) {
      dispatch({ field: 'folders', value: JSON.parse(folders) });
    }

    const prompts = localStorage.getItem('prompts');
    if (prompts) {
      dispatch({ field: 'prompts', value: JSON.parse(prompts) });
    }

    const conversationHistory = localStorage.getItem('conversationHistory');
    if (conversationHistory) {
      const parsedConversationHistory: Conversation[] =
        JSON.parse(conversationHistory);
      const cleanedConversationHistory = cleanConversationHistory(
        parsedConversationHistory,
      );

      dispatch({ field: 'conversations', value: cleanedConversationHistory });
    }

    const selectedConversation = localStorage.getItem('selectedConversation');
    if (selectedConversation) {
      const parsedSelectedConversation: Conversation =
        JSON.parse(selectedConversation);
      const cleanedSelectedConversation = cleanSelectedConversation(
        parsedSelectedConversation,
      );

      dispatch({
        field: 'selectedConversation',
        value: cleanedSelectedConversation,
      });
    } else {
      const lastConversation = conversations[conversations.length - 1];
      dispatch({
        field: 'selectedConversation',
        value: {
          id: uuidv4(),
          name: t('New Conversation'),
          messages: [],
          model: OpenAIModels[defaultModelId],
          prompt: DEFAULT_SYSTEM_PROMPT,
          temperature: lastConversation?.temperature ?? DEFAULT_TEMPERATURE,
          folderId: null,
        },
      });
    }
  }, [
    defaultModelId,
    dispatch,
    serverSideApiKeyIsSet,
    serverSidePluginKeysSet,
  ]);

  return (
    <HomeContext.Provider
      value={{
        ...contextValue,
        handleNewConversation,
        handleCreateFolder,
        handleDeleteFolder,
        handleUpdateFolder,
        handleSelectConversation,
        handleUpdateConversation,
        handleDeleteConversation,
      }}
    >
      <Head>
        <title>LLM Labeling UI</title>
        <meta name="description" content="ChatGPT but better." />
        <meta
          name="viewport"
          content="height=device-height ,width=device-width, initial-scale=1, user-scalable=no"
        />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main
        className={`flex h-screen w-screen flex-col text-sm text-white dark:text-white ${lightMode}`}
      >
        <div className="flex h-full w-full pt-[48px] sm:pt-0">
          <Chatbar />

          <div className="flex flex-1">
            <Chat stopConversationRef={stopConversationRef} />
          </div>

          {/* <Promptbar /> */}
        </div>
      </main>
    </HomeContext.Provider>
  );
};
export default Home;
