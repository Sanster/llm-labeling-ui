import { IconEdit, IconRobot, IconUser } from '@tabler/icons-react';
import { FC, memo, use, useContext, useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';

import { useTranslation } from 'next-i18next';

import { useFetch } from '@/hooks/useFetch';

import { GetTokenCountResponseProps } from '@/services/useApiService';

import { DEFAULT_SYSTEM_PROMPT, DEFAULT_TEMPERATURE } from '@/utils/app/const';
import { updateConversation } from '@/utils/app/conversation';
import HomeContext from '@/utils/home.context';

import { Conversation, Message } from '@/types/chat';
import { OpenAIModelID, OpenAIModels } from '@/types/openai';

import { CodeBlock } from '../Markdown/CodeBlock';
import { MemoizedReactMarkdown } from '../Markdown/MemoizedReactMarkdown';
import { DeleteMessage } from './DeleteChatMessage';
import { SplitConversation } from './SplitConversation';

import rehypeMathjax from 'rehype-mathjax';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { v4 as uuidv4 } from 'uuid';

export interface Props {
  message: Message;
  messageIndex: number;
  tokenData: GetTokenCountResponseProps | undefined;
  onEdit?: (editedMessage: Message, onlySave: Boolean) => void;
}

export const ChatMessage: FC<Props> = memo(
  ({ message, messageIndex, tokenData, onEdit }) => {
    const { t } = useTranslation('chat');
    const fetchService = useFetch();

    const {
      state: {
        selectedConversation,
        conversations,
        currentMessage,
        messageIsStreaming,
      },
      handleSplitConversation,
      dispatch: homeDispatch,
    } = useContext(HomeContext);

    const [isEditing, setIsEditing] = useState<boolean>(false);
    const [isTyping, setIsTyping] = useState<boolean>(false);
    const [messageContent, setMessageContent] = useState(message.content);
    const [messagedCopied, setMessageCopied] = useState(false);

    const [tokenCumulativeCounts, setTokenCumulativeCounts] = useState<
      number[] | undefined
    >(undefined);

    useEffect(() => {
      // 求 tokenData.messagesTokenCounts 的累加和，保存在 tokenCumulativeCounts 中
      const _tokenCumulativeCounts = tokenData?.messagesTokenCounts.reduce(
        (acc, cur) => {
          acc.push((acc.length > 0 ? acc[acc.length - 1] : 0) + cur);
          return acc;
        },
        [] as number[],
      );
      setTokenCumulativeCounts(_tokenCumulativeCounts);
    }, [tokenData]);

    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const toggleEditing = () => {
      setIsEditing(!isEditing);
    };

    const handleInputChange = (
      event: React.ChangeEvent<HTMLTextAreaElement>,
    ) => {
      setMessageContent(event.target.value);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'inherit';
        textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
      }
    };

    const handleEditMessage = () => {
      if (message.content != messageContent) {
        if (selectedConversation && onEdit) {
          onEdit(
            { ...message, content: messageContent },
            message.role === 'assistant',
          );
        }
      }
      setIsEditing(false);
    };

    const handleOnlySaveUserMessage = () => {
      if (message.content != messageContent) {
        if (selectedConversation && onEdit) {
          onEdit({ ...message, content: messageContent }, true);
        }
      }
      setIsEditing(false);
    };

    const handleDeleteMessage = async () => {
      if (!selectedConversation) return;

      const { messages } = selectedConversation;
      const findIndex = messages.findIndex((elm) => elm === message);

      if (findIndex < 0) return;

      if (
        findIndex < messages.length - 1 &&
        messages[findIndex + 1].role === 'assistant'
      ) {
        messages.splice(findIndex, 2);
      } else {
        messages.splice(findIndex, 1);
      }
      const updatedConversation = {
        ...selectedConversation,
        messages,
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
      homeDispatch({ field: 'selectedConversation', value: single });
      homeDispatch({ field: 'conversations', value: all });
    };

    const handlePressEnter = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !isTyping && !e.shiftKey) {
        e.preventDefault();
        handleEditMessage();
      }
    };

    const copyOnClick = () => {
      if (!navigator.clipboard) return;

      navigator.clipboard.writeText(message.content).then(() => {
        setMessageCopied(true);
        setTimeout(() => {
          setMessageCopied(false);
        }, 2000);
      });
    };

    useEffect(() => {
      setMessageContent(message.content);
    }, [message.content]);

    useEffect(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'inherit';
        textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
      }
    }, [isEditing]);

    const renderBotMarkdown = () => {
      return (
        <div className="flex flex-row">
          <MemoizedReactMarkdown
            className="prose dark:prose-invert flex-1"
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeMathjax]}
            components={{
              code({ node, inline, className, children, ...props }) {
                if (children.length) {
                  if (children[0] == '▍') {
                    return (
                      <span className="animate-pulse cursor-default mt-1">
                        ▍
                      </span>
                    );
                  }

                  children[0] = (children[0] as string).replace('`▍`', '▍');
                }

                const match = /language-(\w+)/.exec(className || '');

                return !inline ? (
                  <CodeBlock
                    key={Math.random()}
                    language={(match && match[1]) || ''}
                    value={String(children).replace(/\n$/, '')}
                    {...props}
                  />
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
              table({ children }) {
                return (
                  <table className="border-collapse border border-black px-3 py-1 dark:border-white">
                    {children}
                  </table>
                );
              },
              th({ children }) {
                return (
                  <th className="break-words border border-black bg-gray-500 px-3 py-1 text-white dark:border-white">
                    {children}
                  </th>
                );
              },
              td({ children }) {
                return (
                  <td className="break-words border border-black px-3 py-1 dark:border-white">
                    {children}
                  </td>
                );
              },
            }}
          >
            {`${message.content}${
              messageIsStreaming &&
              messageIndex == (selectedConversation?.messages.length ?? 0) - 1
                ? '`▍`'
                : ''
            }`}
          </MemoizedReactMarkdown>
        </div>
      );
    };

    const userMessageTokenInfo = () => {
      let res = `Round ${messageIndex / 2 + 1}`;
      if (
        tokenData &&
        tokenCumulativeCounts &&
        tokenCumulativeCounts[tokenCumulativeCounts.length - 1] !== 0
      ) {
        res += `, Current round token: ${
          tokenData.messagesTokenCounts[messageIndex] +
          tokenData.messagesTokenCounts[messageIndex + 1]
        }`;

        res += `, Context token: ${
          tokenCumulativeCounts[messageIndex] -
          tokenData.messagesTokenCounts[messageIndex] +
          tokenData.promptTokenCount
        }`;
      }
      return res;
    };

    return (
      <div
        className={`group md:px-4 ${
          message.role === 'assistant'
            ? 'border-b border-black/10 bg-gray-50 text-gray-800 dark:border-gray-900/50 dark:bg-[#444654] dark:text-gray-100'
            : 'border-b border-black/10 bg-white text-gray-800 dark:border-gray-900/50 dark:bg-[#343541] dark:text-gray-100'
        }`}
        style={{ overflowWrap: 'anywhere' }}
      >
        <div className="relative m-auto flex p-4 flex-col text-base md:max-w-2xl lg:max-w-2xl lg:px-0 xl:max-w-3xl">
          {message.role === 'user' && (
            <div className="text-gray-500 dark:text-gray-500">
              {userMessageTokenInfo()}
            </div>
          )}

          <div className="relative flex text-base md:gap-6 md:py-2">
            <div className="min-w-[40px] text-right font-bold">
              {message.role === 'assistant' ? (
                <IconRobot size={30} />
              ) : (
                <IconUser size={30} />
              )}
            </div>

            <div className="prose mt-[-2px] w-full dark:prose-invert">
              <div className="flex w-full">
                {isEditing ? (
                  <div className="flex w-full flex-col">
                    <textarea
                      ref={textareaRef}
                      className="w-full resize-none whitespace-pre-wrap border-none dark:bg-[#343541]"
                      value={messageContent}
                      onChange={handleInputChange}
                      onKeyDown={handlePressEnter}
                      onCompositionStart={() => setIsTyping(true)}
                      onCompositionEnd={() => setIsTyping(false)}
                      style={{
                        fontFamily: 'inherit',
                        fontSize: 'inherit',
                        lineHeight: 'inherit',
                        padding: '0',
                        margin: '0',
                        overflow: 'hidden',
                      }}
                    />

                    <div className="mt-10 flex justify-center space-x-4">
                      {message.role === 'user' ? (
                        <div className="flex gap-3">
                          <button
                            className="h-[40px] rounded-md bg-blue-500 px-4 py-1 text-sm font-medium text-white enabled:hover:bg-blue-600 disabled:opacity-50"
                            onClick={handleOnlySaveUserMessage}
                            disabled={messageContent.trim().length <= 0}
                          >
                            {t('Save')}
                          </button>

                          <button
                            className="h-[40px] rounded-md bg-blue-500 px-4 py-1 text-sm font-medium text-white enabled:hover:bg-blue-600 disabled:opacity-50"
                            onClick={handleEditMessage}
                            disabled={messageContent.trim().length <= 0}
                          >
                            {t('Save & Submit')}
                          </button>
                        </div>
                      ) : (
                        <button
                          className="h-[40px] rounded-md bg-blue-500 px-4 py-1 text-sm font-medium text-white enabled:hover:bg-blue-600 disabled:opacity-50"
                          onClick={handleEditMessage}
                          disabled={messageContent.trim().length <= 0}
                        >
                          {t('Save')}
                        </button>
                      )}

                      <button
                        className="h-[40px] rounded-md border border-neutral-300 px-4 py-1 text-sm font-medium text-neutral-700 hover:bg-neutral-100 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
                        onClick={() => {
                          setMessageContent(message.content);
                          setIsEditing(false);
                        }}
                      >
                        {t('Cancel')}
                      </button>
                    </div>
                  </div>
                ) : message.role === 'user' ? (
                  <div className="prose whitespace-pre-wrap dark:prose-invert flex-1">
                    {message.content}
                  </div>
                ) : (
                  <div className="flex-1">{renderBotMarkdown()}</div>
                )}

                {!isEditing && (
                  <div className="md:-mr-8 ml-1 md:ml-0 flex flex-col md:flex-row gap-4 md:gap-1 items-center md:items-start justify-end md:justify-start">
                    <button
                      className="invisible group-hover:visible focus:visible text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                      onClick={toggleEditing}
                    >
                      <IconEdit size={20} />
                    </button>

                    <DeleteMessage onDeleteMessage={handleDeleteMessage} />

                    {message.role === 'user' && messageIndex !== 0 && (
                      <SplitConversation
                        onSplitConversation={() => {
                          if (selectedConversation) {
                            handleSplitConversation(
                              selectedConversation,
                              messageIndex,
                            );
                          }
                        }}
                      />
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  },
);
ChatMessage.displayName = 'ChatMessage';
