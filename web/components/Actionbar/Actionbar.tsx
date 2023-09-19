import { useContext, useEffect, useState } from 'react';
import toast from 'react-hot-toast';

import { useFetch } from '@/hooks/useFetch';

import { updateConversation } from '@/utils/app/conversation';
import HomeContext from '@/utils/home.context';
import {
  MESSAGE_FILTER_EQUAL,
  MESSAGE_FILTER_GREATER,
  MESSAGE_FILTER_LESS,
  MESSAGE_FILTER_NONE,
} from '@/utils/home.state';
import { replaceAll } from '@/utils/utils';

import { Conversation, Message } from '@/types/chat';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../Accordion/Accordion';
import { Button } from '../Button/Button';
import { Checkbox } from '../CheckBox/CheckBox';
import { Input } from '../Input/Input';
import { Label } from '../Label/Label';
import { RadioGroup, RadioGroupItem } from '../RadioGroup/RadioGroup';
import SimpleSidebar from '../Sidebar/SimpleSidebar';

import { useDebounce } from '@uidotdev/usehooks';

const Actionbar = () => {
  const {
    state: { showPromptbar, selectedConversation, conversations },
    dispatch: homeDispatch,
  } = useContext(HomeContext);
  const fetchService = useFetch();

  const [messageFilterCount, setMessageFilterCount] = useState(0);
  const debouncedMessageFilterCount = useDebounce(messageFilterCount, 300);
  const [messageFilterMode, setMessageFilterMode] =
    useState(MESSAGE_FILTER_NONE);

  useEffect(() => {
    homeDispatch({
      field: 'messageCountFilterCount',
      value: debouncedMessageFilterCount,
    });
  }, [debouncedMessageFilterCount]);

  const [searchText, setSearchText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [matchCase, setMatchCase] = useState(true);

  const handleTogglePromptbar = () => {
    homeDispatch({ field: 'showPromptbar', value: !showPromptbar });
    localStorage.setItem('showPromptbar', JSON.stringify(!showPromptbar));
  };

  const handleSearchTextChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setSearchText(event.target.value);
  };

  const handleReplaceTextChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    setReplaceText(event.target.value);
  };

  const handleMessageFilterCountChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    let newVal = parseInt(event.target.value, 10);
    setMessageFilterCount(newVal);
  };

  const handleMessageFilterModeChange = (newMode: string) => {
    homeDispatch({ field: 'messageCountFilterMode', value: newMode });
    setMessageFilterMode(newMode);
  };

  const handleSubmit = async () => {
    if (selectedConversation && searchText && replaceText) {
      const updatedMessages = selectedConversation.messages.map(
        (v: Message, index: number) => {
          v.content = replaceAll(v.content, searchText, replaceText, matchCase);
          return v;
        },
      );

      const updatedConversation = {
        ...selectedConversation,
        name: replaceAll(
          selectedConversation.name,
          searchText,
          replaceText,
          matchCase,
        ),
        prompt: replaceAll(
          selectedConversation.prompt,
          searchText,
          replaceText,
          matchCase,
        ),
        messages: [...updatedMessages],
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
    }
  };

  const renderActions = () => {
    return (
      <Accordion
        type="multiple"
        defaultValue={['replace-item', 'message-count-filter']}
      >
        <AccordionItem value="message-count-filter">
          <AccordionTrigger>Message Count Filter</AccordionTrigger>
          <AccordionContent>
            <div className="flex flex-col gap-4">
              <RadioGroup
                defaultValue={MESSAGE_FILTER_NONE}
                value={messageFilterMode}
                onValueChange={handleMessageFilterModeChange}
              >
                <div className="flex items-center space-x-2 dark">
                  <RadioGroupItem
                    value={MESSAGE_FILTER_NONE}
                    id={MESSAGE_FILTER_NONE}
                  />
                  <Label htmlFor={MESSAGE_FILTER_NONE}>No filter</Label>
                </div>

                <div className="flex items-center space-x-2 dark">
                  <RadioGroupItem
                    value={MESSAGE_FILTER_EQUAL}
                    id={MESSAGE_FILTER_EQUAL}
                  />
                  <Label htmlFor={MESSAGE_FILTER_EQUAL}>Equal</Label>
                </div>

                <div className="flex items-center space-x-2 dark">
                  <RadioGroupItem
                    value={MESSAGE_FILTER_GREATER}
                    id={MESSAGE_FILTER_GREATER}
                  />
                  <Label htmlFor={MESSAGE_FILTER_GREATER}>Greater</Label>
                </div>

                <div className="flex items-center space-x-2 dark">
                  <RadioGroupItem
                    value={MESSAGE_FILTER_LESS}
                    id={MESSAGE_FILTER_LESS}
                  />
                  <Label htmlFor={MESSAGE_FILTER_LESS}>Less</Label>
                </div>
              </RadioGroup>

              <Input
                type="number"
                placeholder="Message Count"
                value={messageFilterCount}
                onChange={handleMessageFilterCountChange}
              />
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="replace-item">
          <AccordionTrigger>Replace String</AccordionTrigger>
          <AccordionContent>
            <div className="flex flex-col gap-4">
              <div className="grid w-full max-w-sm items-center gap-1.5">
                <Label htmlFor="original">Search</Label>
                <Input
                  type="text"
                  id="original"
                  placeholder="Search"
                  value={searchText}
                  onChange={handleSearchTextChange}
                />
              </div>
              <div className="grid w-full max-w-sm items-center gap-1.5">
                <Label htmlFor="replacewith">Replace</Label>
                <Input
                  type="text"
                  id="replacewith"
                  placeholder="Replace"
                  value={replaceText}
                  onChange={handleReplaceTextChange}
                />
              </div>

              <div className="flex items-center w-full gap-8">
                <div className="flex gap-2">
                  <Checkbox
                    id="match-case"
                    className="dark"
                    checked={matchCase}
                    onCheckedChange={(v) => setMatchCase(v as boolean)}
                  />
                  <Label htmlFor="match-case">Match Case</Label>
                </div>
              </div>

              <Button variant="outline" onClick={handleSubmit}>
                Run
              </Button>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    );
  };

  return (
    <SimpleSidebar
      side={'right'}
      isOpen={showPromptbar}
      component={renderActions()}
      toggleOpen={handleTogglePromptbar}
    />
  );
};

export default Actionbar;
