import { useCallback } from 'react';

import { useFetch } from '@/hooks/useFetch';

import { Conversation } from '@/types/chat';

export interface GetModelsRequestProps {
  key: string;
  org: string;
}

export interface GetConversationsRequestProps {
  page: number;
  pageSize: number;
}

export interface GetTokenCountRequestProps {
  text: string;
}
export interface GetTokenCountResponseProps {
  count: number;
}

interface ConversationResponse {
  created_at: string;
  updated_at: string;
  id: string;
  data: Conversation;
}

export interface GetConversationsResponseProps {
  totalPages: number;
  page: number;
  conversations: ConversationResponse[];
  totalConversations: number;
}

const useApiService = () => {
  const fetchService = useFetch();

  const getModels = useCallback(
    (params: GetModelsRequestProps, signal?: AbortSignal) => {
      return fetchService.post<GetModelsRequestProps>(`/api/models`, {
        body: { key: params.key, org: params.org },
        headers: {
          'Content-Type': 'application/json',
        },
        signal,
      });
    },
    [fetchService],
  );

  const getConversations = useCallback(
    (params: GetConversationsRequestProps, signal?: AbortSignal) => {
      return fetchService.post<GetConversationsResponseProps>(
        `/api/conversations`,
        {
          body: { page: params.page, pageSize: params.pageSize },
          headers: {
            'Content-Type': 'application/json',
          },
          signal,
        },
      );
    },
    [fetchService],
  );

  const getTokenCount = useCallback(
    (params: GetTokenCountRequestProps, signal?: AbortSignal) => {
      return fetchService.post<GetTokenCountResponseProps>(
        `/api/count_tokens`,
        {
          body: params,
          headers: {
            'Content-Type': 'application/json',
          },
          signal,
        },
      );
    },
    [fetchService],
  );

  return {
    getModels,
    getConversations,
    getTokenCount,
  };
};

export default useApiService;
