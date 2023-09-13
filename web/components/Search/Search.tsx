import { IconX } from '@tabler/icons-react';
import { FC, useEffect, useState } from 'react';

import { useTranslation } from 'next-i18next';

import { useDebounce } from '@uidotdev/usehooks';

interface Props {
  placeholder: string;
  searchTerm: string;
  onSearch: (searchTerm: string) => void;
}
const Search: FC<Props> = ({ placeholder, searchTerm, onSearch }) => {
  const { t } = useTranslation('sidebar');

  const [newSearchTerm, setNewSearchTerm] = useState(searchTerm);
  const debouncedNewSearchTerm = useDebounce(newSearchTerm, 500);

  useEffect(() => {
    onSearch(debouncedNewSearchTerm);
  }, [debouncedNewSearchTerm]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('search change');
    setNewSearchTerm(e.target.value);
  };

  const clearSearch = () => {
    onSearch('');
    setNewSearchTerm('');
  };

  return (
    <div className="relative flex items-center">
      <input
        className="w-full flex-1 rounded-md border border-neutral-600 bg-[#202123] px-4 py-3 pr-10 text-[14px] leading-3 text-white"
        type="text"
        placeholder={t(placeholder) || ''}
        value={newSearchTerm}
        onChange={handleSearchChange}
      />

      {newSearchTerm && (
        <IconX
          className="absolute right-4 cursor-pointer text-neutral-300 hover:text-neutral-400"
          size={18}
          onClick={clearSearch}
        />
      )}
    </div>
  );
};

export default Search;
